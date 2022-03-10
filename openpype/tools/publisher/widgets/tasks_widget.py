from Qt import QtCore, QtGui

from openpype.tools.utils.tasks_widget import TasksWidget, TASK_NAME_ROLE


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
    def __init__(self, controller, allow_empty_task=False):
        super(TasksModel, self).__init__()

        self._allow_empty_task = allow_empty_task
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
        if asset_name not in self._task_names_by_asset_name:
            return False

        if self._allow_empty_task and not task_name:
            return True

        task_names = self._task_names_by_asset_name[asset_name]
        if task_name in task_names:
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
        if self._allow_empty_task:
            new_task_names.add("")
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
            item.setData(task_name, TASK_NAME_ROLE)
            self._items_by_name[task_name] = item
            new_items.append(item)

        if new_items:
            root_item.appendRows(new_items)

    def headerData(self, section, orientation, role=None):
        if role is None:
            role = QtCore.Qt.EditRole
        # Show nice labels in the header
        if section == 0:
            if (
                role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole)
                and orientation == QtCore.Qt.Horizontal
            ):
                return "Tasks"

        return super(TasksModel, self).headerData(section, orientation, role)


class CreateDialogTasksWidget(TasksWidget):
    def __init__(self, controller, parent):
        self._controller = controller
        super(CreateDialogTasksWidget, self).__init__(None, parent)

        self._enabled = None

    def _create_source_model(self):
        return TasksModel(self._controller)

    def set_asset_name(self, asset_name):
        current = self.get_selected_task_name()
        if current:
            self._last_selected_task_name = current

        self._tasks_model.set_asset_names([asset_name])
        if self._last_selected_task_name and self._enabled:
            self.select_task_name(self._last_selected_task_name)

        # Force a task changed emit.
        self.task_changed.emit()

    def select_task_name(self, task_name):
        super(CreateDialogTasksWidget, self).select_task_name(task_name)
        if not self._enabled:
            current = self.get_selected_task_name()
            if current:
                self._last_selected_task_name = current
            self._clear_selection()

    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            last_selected_task_name = self.get_selected_task_name()
            if last_selected_task_name:
                self._last_selected_task_name = last_selected_task_name
            self._clear_selection()

        elif self._last_selected_task_name is not None:
            self.select_task_name(self._last_selected_task_name)
