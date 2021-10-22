import re
import collections

from Qt import QtCore, QtGui


class AssetsHierarchyModel(QtGui.QStandardItemModel):
    """Assets hiearrchy model.

    For selecting asset for which should beinstance created.

    Uses controller to load asset hierarchy. All asset documents are stored by
    their parents.
    """
    def __init__(self, controller):
        super(AssetsHierarchyModel, self).__init__()
        self._controller = controller

        self._items_by_name = {}

    def reset(self):
        self.clear()

        self._items_by_name = {}
        assets_by_parent_id = self._controller.get_asset_hierarchy()

        items_by_name = {}
        _queue = collections.deque()
        _queue.append((self.invisibleRootItem(), None))
        while _queue:
            parent_item, parent_id = _queue.popleft()
            children = assets_by_parent_id.get(parent_id)
            if not children:
                continue

            children_by_name = {
                child["name"]: child
                for child in children
            }
            items = []
            for name in sorted(children_by_name.keys()):
                child = children_by_name[name]
                item = QtGui.QStandardItem(name)
                items_by_name[name] = item
                items.append(item)
                _queue.append((item, child["_id"]))

            parent_item.appendRows(items)

        self._items_by_name = items_by_name

    def name_is_valid(self, item_name):
        return item_name in self._items_by_name

    def get_index_by_name(self, item_name):
        item = self._items_by_name.get(item_name)
        if item:
            return item.index()
        return QtCore.QModelIndex()


class TasksModel(QtGui.QStandardItemModel):
    """Tasks model.

    Task model must have set context of asset documents.

    Items in model are based on 0-infinite asset documents. Always contain
    an interserction of context asset tasks. When no assets are in context
    them model is empty if 2 or more are in context assets that don't have
    tasks with same names then model is empty too.

    Args:
        controller (PublisherController): Controller which handles creation and
            publishing.
    """
    def __init__(self, controller):
        super(TasksModel, self).__init__()
        self._controller = controller
        self._items_by_name = {}
        self._asset_names = []
        self._task_names_by_asset_name = {}

    def set_asset_names(self, asset_names):
        """Set assets context."""
        self._asset_names = asset_names
        self.reset()

    @staticmethod
    def get_intersection_of_tasks(task_names_by_asset_name):
        """Calculate intersection of task names from passed data.

        Example:
        ```
        # Passed `task_names_by_asset_name`
        {
            "asset_1": ["compositing", "animation"],
            "asset_2": ["compositing", "editorial"]
        }
        ```
        Result:
        ```
        # Set
        {"compositing"}
        ```

        Args:
            task_names_by_asset_name (dict): Task names in iterable by parent.
        """
        tasks = None
        for task_names in task_names_by_asset_name.values():
            if tasks is None:
                tasks = set(task_names)
            else:
                tasks &= set(task_names)

            if not tasks:
                break
        return tasks or set()

    def is_task_name_valid(self, asset_name, task_name):
        """Is task name available for asset.

        Args:
            asset_name (str): Name of asset where should look for task.
            task_name (str): Name of task which should be available in asset's
                tasks.
        """
        task_names = self._task_names_by_asset_name.get(asset_name)
        if task_names and task_name in task_names:
            return True
        return False

    def reset(self):
        """Update model by current context."""
        if not self._asset_names:
            self._items_by_name = {}
            self._task_names_by_asset_name = {}
            self.clear()
            return

        task_names_by_asset_name = (
            self._controller.get_task_names_by_asset_names(self._asset_names)
        )
        self._task_names_by_asset_name = task_names_by_asset_name

        new_task_names = self.get_intersection_of_tasks(
            task_names_by_asset_name
        )
        old_task_names = set(self._items_by_name.keys())
        if new_task_names == old_task_names:
            return

        root_item = self.invisibleRootItem()
        for task_name in old_task_names:
            if task_name not in new_task_names:
                item = self._items_by_name.pop(task_name)
                root_item.removeRow(item.row())

        new_items = []
        for task_name in new_task_names:
            if task_name in self._items_by_name:
                continue

            item = QtGui.QStandardItem(task_name)
            self._items_by_name[task_name] = item
            new_items.append(item)
        root_item.appendRows(new_items)


class RecursiveSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Recursive proxy model.

    Item is not filtered if any children match the filter.

    Use case: Filtering by string - parent won't be filtered if does not match
        the filter string but first checks if any children does.
    """
    def filterAcceptsRow(self, row, parent_index):
        regex = self.filterRegExp()
        if not regex.isEmpty():
            model = self.sourceModel()
            source_index = model.index(
                row, self.filterKeyColumn(), parent_index
            )
            if source_index.isValid():
                pattern = regex.pattern()

                # Check current index itself
                value = model.data(source_index, self.filterRole())
                if re.search(pattern, value, re.IGNORECASE):
                    return True

                rows = model.rowCount(source_index)
                for idx in range(rows):
                    if self.filterAcceptsRow(idx, source_index):
                        return True
                return False

        return super(RecursiveSortFilterProxyModel, self).filterAcceptsRow(
            row, parent_index
        )
