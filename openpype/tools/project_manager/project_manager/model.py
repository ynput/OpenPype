import collections
import copy
import json
from uuid import uuid4

from pymongo import UpdateOne, DeleteOne

from Qt import QtCore, QtGui

from .constants import (
    IDENTIFIER_ROLE,
    ITEM_TYPE_ROLE,
    DUPLICATED_ROLE,
    HIERARCHY_CHANGE_ABLE_ROLE,
    REMOVED_ROLE,
    EDITOR_OPENED_ROLE,
    PROJECT_NAME_ROLE
)
from .style import ResourceCache

from openpype.lib import CURRENT_DOC_SCHEMAS


class ProjectModel(QtGui.QStandardItemModel):
    """Load possible projects to modify from MongoDB.

    Mongo collection must contain project document with "type" "project" and
    matching "name" value with name of collection.
    """

    def __init__(self, dbcon, *args, **kwargs):
        self.dbcon = dbcon

        self._items_by_name = {}

        super(ProjectModel, self).__init__(*args, **kwargs)

    def refresh(self):
        """Reload projects."""
        self.dbcon.Session["AVALON_PROJECT"] = None

        new_project_items = []

        if None not in self._items_by_name:
            none_project = QtGui.QStandardItem("< Select Project >")
            self._items_by_name[None] = none_project
            new_project_items.append(none_project)

        project_docs = self.dbcon.projects(
            projection={"name": 1},
            only_active=True
        )
        project_names = set()
        for project_doc in project_docs:
            project_name = project_doc.get("name")
            if not project_name:
                continue

            project_names.add(project_name)
            if project_name not in self._items_by_name:
                project_item = QtGui.QStandardItem(project_name)
                project_item.setData(project_name, PROJECT_NAME_ROLE)

                self._items_by_name[project_name] = project_item
                new_project_items.append(project_item)

        root_item = self.invisibleRootItem()
        for project_name in tuple(self._items_by_name.keys()):
            if project_name is None or project_name in project_names:
                continue
            project_item = self._items_by_name.pop(project_name)
            root_item.removeRow(project_item.row())

        if new_project_items:
            root_item.appendRows(new_project_items)


class ProjectProxyFilter(QtCore.QSortFilterProxyModel):
    """Filters default project item."""
    def __init__(self, *args, **kwargs):
        super(ProjectProxyFilter, self).__init__(*args, **kwargs)
        self._filter_default = False

    def set_filter_default(self, enabled=True):
        """Set if filtering of default item is enabled."""
        if enabled == self._filter_default:
            return
        self._filter_default = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if not self._filter_default:
            return True

        model = self.sourceModel()
        source_index = model.index(row, self.filterKeyColumn(), parent)
        return source_index.data(PROJECT_NAME_ROLE) is not None


class HierarchySelectionModel(QtCore.QItemSelectionModel):
    """Selection model with defined allowed multiselection columns.

    This model allows to select multiple rows and enter one of their
    editors to edit value of all selected rows.
    """

    def __init__(self, multiselection_columns, *args, **kwargs):
        super(HierarchySelectionModel, self).__init__(*args, **kwargs)
        self.multiselection_columns = multiselection_columns

    def setCurrentIndex(self, index, command):
        if index.column() in self.multiselection_columns:
            if (
                command & QtCore.QItemSelectionModel.Clear
                and command & QtCore.QItemSelectionModel.Select
            ):
                command = QtCore.QItemSelectionModel.NoUpdate
        super(HierarchySelectionModel, self).setCurrentIndex(index, command)


class HierarchyModel(QtCore.QAbstractItemModel):
    """Main model for hierarchy modification and value changes.

    Main part of ProjectManager.

    Model should be able to load existing entities, create new, handle their
    validations like name duplication and validate if is possible to save its
    data.

    Args:
        dbcon (AvalonMongoDB): Connection to MongoDB with set AVALON_PROJECT in
            its Session to current project.
    """

    # Definition of all possible columns with their labels in default order
    # - order is important as column names are used as keys for column indexes
    _columns_def = [
        ("name", "Name"),
        ("type", "Type"),
        ("fps", "FPS"),
        ("frameStart", "Frame start"),
        ("frameEnd", "Frame end"),
        ("handleStart", "Handle start"),
        ("handleEnd", "Handle end"),
        ("resolutionWidth", "Width"),
        ("resolutionHeight", "Height"),
        ("clipIn", "Clip in"),
        ("clipOut", "Clip out"),
        ("pixelAspect", "Pixel aspect"),
        ("tools_env", "Tools")
    ]
    # Columns allowing multiselection in edit mode
    # - gives ability to set all of keys below on multiple items at once
    multiselection_columns = {
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight",
        "handleStart",
        "handleEnd",
        "clipIn",
        "clipOut",
        "pixelAspect",
        "tools_env"
    }
    columns = [
        item[0]
        for item in _columns_def
    ]
    columns_len = len(columns)
    column_labels = {
        idx: item[1]
        for idx, item in enumerate(_columns_def)
    }

    index_moved = QtCore.Signal(QtCore.QModelIndex)
    project_changed = QtCore.Signal()

    def __init__(self, dbcon, parent=None):
        super(HierarchyModel, self).__init__(parent)

        self.multiselection_column_indexes = {
            self.columns.index(key)
            for key in self.multiselection_columns
        }

        # TODO Reset them on project change
        self._current_project = None
        self._root_item = None
        self._items_by_id = {}
        self._asset_items_by_name = collections.defaultdict(set)
        self.dbcon = dbcon

        self._reset_root_item()

    @property
    def items_by_id(self):
        return self._items_by_id

    def _reset_root_item(self):
        """Removes all previous content related to model."""
        self._root_item = RootItem(self)

    def refresh_project(self):
        """Reload project data and discard unsaved changes."""
        self.set_project(self._current_project, True)

    @property
    def project_item(self):
        """Access to current project item.

        Model can have 0-1 ProjectItems at once.
        """
        output = None
        for row in range(self._root_item.rowCount()):
            item = self._root_item.child(row)
            if isinstance(item, ProjectItem):
                output = item
                break
        return output

    def set_project(self, project_name, force=False):
        """Change project and discard unsaved changes.

        Args:
            project_name(str): New project name. Or None if just clearing
                content.
            force(bool): Force to change project even if project name is same
                as current project.
        """
        if self._current_project == project_name and not force:
            return

        # Reset attributes
        self._items_by_id.clear()
        self._asset_items_by_name.clear()

        self.clear()

        self._current_project = project_name

        # Skip if project is None
        if not project_name:
            return

        # Find project'd document
        project_doc = self.dbcon.database[project_name].find_one(
            {"type": "project"},
            ProjectItem.query_projection
        )
        # Skip if project document does not exist
        # - this shouldn't happen using only UI elements
        if not project_doc:
            return

        # Create project item
        project_item = ProjectItem(project_doc)
        self.add_item(project_item)

        # Query all assets of the project
        asset_docs = self.dbcon.database[project_name].find(
            {"type": "asset"},
            AssetItem.query_projection
        )
        asset_docs_by_id = {
            asset_doc["_id"]: asset_doc
            for asset_doc in asset_docs
        }

        # Check if asset have published content and prepare booleans
        #   if asset item can be modified (name and hierarchy change)
        # - the same must be applied to all it's parents
        asset_ids = list(asset_docs_by_id.keys())
        result = []
        if asset_ids:
            result = self.dbcon.database[project_name].aggregate([
                {
                    "$match": {
                        "type": "subset",
                        "parent": {"$in": asset_ids}
                    }
                },
                {
                    "$group": {
                        "_id": "$parent",
                        "count": {"$sum": 1}
                    }
                }
            ])

        asset_modifiable = {
            asset_id: True
            for asset_id in asset_docs_by_id.keys()
        }
        for item in result:
            asset_id = item["_id"]
            count = item["count"]
            asset_modifiable[asset_id] = count < 1

        # Store assets by their visual parent to be able create their hierarchy
        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in asset_docs_by_id.values():
            parent_id = asset_doc["data"].get("visualParent")
            asset_docs_by_parent_id[parent_id].append(asset_doc)

        appending_queue = collections.deque()
        appending_queue.append((None, project_item))

        asset_items_by_id = {}
        non_modifiable_items = set()
        while appending_queue:
            parent_id, parent_item = appending_queue.popleft()
            asset_docs = asset_docs_by_parent_id.get(parent_id) or []

            new_items = []
            for asset_doc in sorted(asset_docs, key=lambda item: item["name"]):
                # Create new Item
                new_item = AssetItem(asset_doc)
                # Store item to be added under parent in bulk
                new_items.append(new_item)

                # Store item by id for task processing
                asset_id = asset_doc["_id"]
                if not asset_modifiable[asset_id]:
                    non_modifiable_items.add(new_item.id)

                asset_items_by_id[asset_id] = new_item
                # Add item to appending queue
                appending_queue.append((asset_id, new_item))

            if new_items:
                self.add_items(new_items, parent_item)

        # Handle Asset's that are not modifiable
        # - pass the information to all it's parents
        non_modifiable_queue = collections.deque()
        for item_id in non_modifiable_items:
            non_modifiable_queue.append(item_id)

        while non_modifiable_queue:
            item_id = non_modifiable_queue.popleft()
            item = self._items_by_id[item_id]
            item.setData(False, HIERARCHY_CHANGE_ABLE_ROLE)

            parent = item.parent()
            if (
                isinstance(parent, AssetItem)
                and parent.id not in non_modifiable_items
            ):
                non_modifiable_items.add(parent.id)
                non_modifiable_queue.append(parent.id)

        # Add task items
        for asset_id, asset_item in asset_items_by_id.items():
            asset_doc = asset_docs_by_id[asset_id]
            asset_tasks = asset_doc["data"]["tasks"]
            if not asset_tasks:
                continue

            task_items = []
            for task_name in sorted(asset_tasks.keys()):
                _task_data = copy.deepcopy(asset_tasks[task_name])
                _task_data["name"] = task_name
                task_item = TaskItem(_task_data)
                task_items.append(task_item)

            self.add_items(task_items, asset_item)

        # Emit that project was successfully changed
        self.project_changed.emit()

    def rowCount(self, parent=None):
        """Number of rows for passed parent."""
        if parent is None or not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.rowCount()

    def columnCount(self, *args, **kwargs):
        """Number of columns is static for this model."""
        return self.columns_len

    def data(self, index, role):
        """Access data for passed index and it's role.

        Model is using principles implemented in BaseItem so converts passed
        index column into key and ask item to return value for passed role.
        """
        if not index.isValid():
            return None

        column = index.column()
        key = self.columns[column]

        item = index.internalPointer()
        return item.data(role, key)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Store data to passed index under role.

        Pass values to corresponding item and behave by it's result.
        """
        if not index.isValid():
            return False

        item = index.internalPointer()
        column = index.column()
        key = self.columns[column]
        # Capture asset name changes for duplcated asset names validation.
        if (
            key == "name"
            and role in (QtCore.Qt.EditRole, QtCore.Qt.DisplayRole)
        ):
            self._rename_asset(item, value)

        # Pass values to item and by result emi dataChanged signal or not
        result = item.setData(value, role, key)
        if result:
            self.dataChanged.emit(index, index, [role])

        return result

    def headerData(self, section, orientation, role):
        """Header labels."""
        if role == QtCore.Qt.DisplayRole:
            if section < self.columnCount():
                return self.column_labels[section]

        return super(HierarchyModel, self).headerData(
            section, orientation, role
        )

    def flags(self, index):
        """Index flags are defined by corresponding item."""
        item = index.internalPointer()
        if item is None:
            return QtCore.Qt.NoItemFlags
        column = index.column()
        key = self.columns[column]
        return item.flags(key)

    def parent(self, index=None):
        """Parent for passed index as QModelIndex.

        Args:
            index(QModelIndex): Parent index. Root item is used if not passed.
        """
        if not index.isValid():
            return QtCore.QModelIndex()

        item = index.internalPointer()
        parent_item = item.parent()

        # If it has no parents we return invalid
        if not parent_item or parent_item is self._root_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def index(self, row, column, parent=None):
        """Return index for row/column under parent.

        Args:
            row(int): Row number.
            column(int): Column number.
            parent(QModelIndex): Parent index. Root item is used if not passed.
        """
        parent_item = None
        if parent is not None and parent.isValid():
            parent_item = parent.internalPointer()

        return self.index_from_item(row, column, parent_item)

    def index_for_item(self, item, column=0):
        """Index for passed item.

        This is for cases that index operations are required on specific item.

        Args:
            item(BaseItem): Item from model that will be converted to
                corresponding QModelIndex.
            column(int): Which column will be part of returned index. By
                default is used column 0.
        """
        return self.index_from_item(
            item.row(), column, item.parent()
        )

    def index_from_item(self, row, column, parent=None):
        """Index for passed row, column and parent item.

        Same implementation as `index` method but "parent" is one of
        BaseItem objects instead of QModelIndex.

        Args:
            row(int): Row number.
            column(int): Column number.
            parent(BaseItem): Parent item. Root item is used if not passed.
        """
        if parent is None:
            parent = self._root_item

        child_item = parent.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)

        return QtCore.QModelIndex()

    def add_new_asset(self, source_index):
        """Create new asset item in hierarchy.

        Args:
            source_index(QModelIndex): Parent under which new asset will be
                added.
        """
        item_id = source_index.data(IDENTIFIER_ROLE)
        item = self.items_by_id[item_id]

        if isinstance(item, TaskItem):
            item = item.parent()

        if isinstance(item, (RootItem, ProjectItem)):
            name = "ep"
            new_row = None
        elif isinstance(item, AssetItem):
            name = None
            new_row = item.rowCount()
        else:
            return

        asset_data = {}
        if name:
            asset_data["name"] = name

        new_child = AssetItem(asset_data)

        result = self.add_item(new_child, item, new_row)
        if result is not None:
            # WARNING Expecting result is index for column 0 ("name")
            new_name = result.data(QtCore.Qt.EditRole)
            self._validate_asset_duplicity(new_name)

        return result

    def add_new_task(self, parent_index):
        """Create new TaskItem under passed parent index or it's parent.

        Args:
            parent_index(QModelIndex): Index of parent AssetItem under which
                will be task added. If index represents TaskItem it's parent is
                used as parent.
        """
        item_id = parent_index.data(IDENTIFIER_ROLE)
        item = self.items_by_id[item_id]

        if isinstance(item, TaskItem):
            parent = item.parent()
        else:
            parent = item

        if not isinstance(parent, AssetItem):
            return None

        new_child = TaskItem()
        return self.add_item(new_child, parent)

    def add_items(self, items, parent=None, start_row=None):
        """Add new items with definition of QAbstractItemModel.

        Trigger `beginInsertRows` and `endInsertRows` to trigger proper
        callbacks in view or proxy model.

        Args:
            items(list[BaseItem]): List of item that will be inserted in model.
            parent(RootItem, ProjectItem, AssetItem): Parent of items under
                which will be items added. Root item is used if not passed.
            start_row(int): Define to which row will be items added. Next
                available row of parent is used if not passed.
        """
        if parent is None:
            parent = self._root_item

        if parent.data(REMOVED_ROLE):
            return []

        if start_row is None:
            start_row = parent.rowCount()

        end_row = start_row + len(items) - 1

        parent_index = self.index_from_item(parent.row(), 0, parent.parent())

        self.beginInsertRows(parent_index, start_row, end_row)

        for idx, item in enumerate(items):
            row = start_row + idx
            if item.parent() is not parent:
                item.set_parent(parent)

            parent.add_child(item, row)

            if isinstance(item, AssetItem):
                name = item.data(QtCore.Qt.EditRole, "name")
                self._asset_items_by_name[name].add(item.id)

            if item.id not in self._items_by_id:
                self._items_by_id[item.id] = item

        self.endInsertRows()

        indexes = []
        for row in range(start_row, end_row + 1):
            indexes.append(
                self.index_from_item(row, 0, parent)
            )
        return indexes

    def add_item(self, item, parent=None, row=None):
        """Add single item into model."""
        result = self.add_items([item], parent, row)
        if result:
            return result[0]
        return None

    def remove_delete_flag(self, item_ids, with_children=True):
        """Remove deletion flag from items with matching ids.

        The flag is also removed from all parents of passed children as it
        wouldn't make sense to not to do so.

        Children of passed item ids are by default also unset for deletion.

        Args:
            list(uuid4): Ids of model items where remove flag should be unset.
            with_children(bool): Unset remove flag also on all children of
                passed items.
        """
        items_by_id = {}
        for item_id in item_ids:
            if item_id in items_by_id:
                continue

            item = self.items_by_id[item_id]
            if isinstance(item, (AssetItem, TaskItem)):
                items_by_id[item_id] = item

        for item in tuple(items_by_id.values()):
            parent = item.parent()
            while True:
                if not isinstance(parent, (AssetItem, TaskItem)):
                    break

                if parent.id not in items_by_id:
                    items_by_id[parent.id] = parent

                parent = parent.parent()

            if not with_children:
                continue

            def _children_recursion(_item):
                if not isinstance(_item, AssetItem):
                    return

                for row in range(_item.rowCount()):
                    _child_item = _item.child(row)
                    if _child_item.id in items_by_id:
                        continue

                    items_by_id[_child_item.id] = _child_item
                    _children_recursion(_child_item)

            _children_recursion(item)

        for item in items_by_id.values():
            if item.data(REMOVED_ROLE):
                item.setData(False, REMOVED_ROLE)
                if isinstance(item, AssetItem):
                    name = item.data(QtCore.Qt.EditRole, "name")
                    self._asset_items_by_name[name].add(item.id)
                    self._validate_asset_duplicity(name)

    def delete_index(self, index):
        """Delete item of the index from model."""
        return self.delete_indexes([index])

    def delete_indexes(self, indexes):
        """Delete items from model."""
        items_by_id = {}
        processed_ids = set()
        for index in indexes:
            if not index.isValid():
                continue

            item_id = index.data(IDENTIFIER_ROLE)
            # There may be indexes for multiple columns
            if item_id not in processed_ids:
                processed_ids.add(item_id)

                item = self._items_by_id[item_id]
                if isinstance(item, (TaskItem, AssetItem)):
                    items_by_id[item_id] = item

        if not items_by_id:
            return

        for item in items_by_id.values():
            self._remove_item(item)

    def _remove_item(self, item):
        """Remove item from model or mark item for deletion.

        Deleted items are using definition of QAbstractItemModel which call
        `beginRemoveRows` and `endRemoveRows` to trigger proper view and proxy
        model callbacks.

        Item is not just removed but is checked if can be removed from model or
        just mark it for deletion for save.

        First of all will find all related children and based on their
        attributes define if can be removed.
        """
        # Skip if item is already marked for deletion
        is_removed = item.data(REMOVED_ROLE)
        if is_removed:
            return

        parent = item.parent()

        # Find all descendants and store them by parent id
        all_descendants = collections.defaultdict(dict)
        all_descendants[parent.id][item.id] = item

        def _fill_children(_all_descendants, cur_item, parent_item=None):
            if parent_item is not None:
                _all_descendants[parent_item.id][cur_item.id] = cur_item

            if isinstance(cur_item, TaskItem):
                was_removed = cur_item.data(REMOVED_ROLE)
                task_removed = True
                if not was_removed and parent_item is not None:
                    task_removed = parent_item.data(REMOVED_ROLE)
                if not was_removed:
                    cur_item.setData(task_removed, REMOVED_ROLE)
                return task_removed

            remove_item = True
            task_children = []
            for row in range(cur_item.rowCount()):
                child_item = cur_item.child(row)
                if isinstance(child_item, TaskItem):
                    task_children.append(child_item)
                    continue

                if not _fill_children(_all_descendants, child_item, cur_item):
                    remove_item = False

            if remove_item:
                cur_item.setData(True, REMOVED_ROLE)
                if isinstance(cur_item, AssetItem):
                    self._rename_asset(cur_item, None)

            # Process tasks as last because their logic is based on parent
            # - tasks may be processed before parent check all asset children
            for task_item in task_children:
                _fill_children(_all_descendants, task_item, cur_item)
            return remove_item

        _fill_children(all_descendants, item)

        modified_children = []
        while all_descendants:
            for parent_id in tuple(all_descendants.keys()):
                children = all_descendants[parent_id]
                if not children:
                    all_descendants.pop(parent_id)
                    continue

                parent_children = {}
                all_without_children = True
                for child_id in tuple(children.keys()):
                    if child_id in all_descendants:
                        all_without_children = False
                        break
                    parent_children[child_id] = children[child_id]

                if not all_without_children:
                    continue

                # Row ranges of items to remove
                # - store tuples of row "start", "end" (can be the same)
                row_ranges = []
                # Predefine start, end variables
                start_row = end_row = None
                chilren_by_row = {}
                parent_item = self._items_by_id[parent_id]
                for row in range(parent_item.rowCount()):
                    child_item = parent_item.child(row)
                    child_id = child_item.id
                    # Not sure if this can happen
                    # TODO validate this line it seems dangerous as start/end
                    #   row is not changed
                    if child_id not in children:
                        continue

                    chilren_by_row[row] = child_item
                    children.pop(child_item.id)

                    removed_mark = child_item.data(REMOVED_ROLE)
                    if not removed_mark or not child_item.is_new:
                        # Skip row sequence store child for later processing
                        #   and store current start/end row range
                        modified_children.append(child_item)
                        if end_row is not None:
                            row_ranges.append((start_row, end_row))
                        start_row = end_row = None
                        continue

                    end_row = row
                    if start_row is None:
                        start_row = row

                if end_row is not None:
                    row_ranges.append((start_row, end_row))

                if not row_ranges:
                    continue

                # Remove items from model
                parent_index = self.index_for_item(parent_item)
                for start, end in row_ranges:
                    self.beginRemoveRows(parent_index, start, end)

                    for idx in range(start, end + 1):
                        child_item = chilren_by_row[idx]
                        # Force name validation
                        if isinstance(child_item, AssetItem):
                            self._rename_asset(child_item, None)
                        child_item.set_parent(None)
                        self._items_by_id.pop(child_item.id)

                    self.endRemoveRows()

        # Trigger data change to repaint items
        # - `BackgroundRole` is random role without any specific reason
        for item in modified_children:
            s_index = self.index_for_item(item)
            e_index = self.index_for_item(item, column=self.columns_len - 1)
            self.dataChanged.emit(s_index, e_index, [QtCore.Qt.BackgroundRole])

    def _rename_asset(self, asset_item, new_name):
        if not isinstance(asset_item, AssetItem):
            return

        prev_name = asset_item.data(QtCore.Qt.EditRole, "name")
        if prev_name == new_name:
            return

        if asset_item.id in self._asset_items_by_name[prev_name]:
            self._asset_items_by_name[prev_name].remove(asset_item.id)

        self._validate_asset_duplicity(prev_name)

        if new_name is None:
            return
        self._asset_items_by_name[new_name].add(asset_item.id)

        self._validate_asset_duplicity(new_name)

    def _validate_asset_duplicity(self, name):
        if name not in self._asset_items_by_name:
            return

        item_ids = self._asset_items_by_name[name]
        if not item_ids:
            self._asset_items_by_name.pop(name)

        elif len(item_ids) == 1:
            for item_id in item_ids:
                item = self._items_by_id[item_id]
            index = self.index_for_item(item)
            self.setData(index, False, DUPLICATED_ROLE)

        else:
            for item_id in item_ids:
                item = self._items_by_id[item_id]
                index = self.index_for_item(item)
                self.setData(index, True, DUPLICATED_ROLE)

    def _move_horizontal_single(self, index, direction):
        if not index.isValid():
            return

        item_id = index.data(IDENTIFIER_ROLE)
        if item_id is None:
            return

        item = self._items_by_id[item_id]
        if isinstance(item, (RootItem, ProjectItem)):
            return

        if item.data(REMOVED_ROLE):
            return

        if (
            isinstance(item, AssetItem)
            and not item.data(HIERARCHY_CHANGE_ABLE_ROLE)
        ):
            return

        if abs(direction) != 1:
            return

        # Move under parent of parent
        src_row = item.row()
        src_parent = item.parent()
        src_parent_index = self.index_from_item(
            src_parent.row(), 0, src_parent.parent()
        )

        dst_row = None
        dst_parent = None

        if direction == -1:
            if isinstance(src_parent, (RootItem, ProjectItem)):
                return
            dst_parent = src_parent.parent()
            dst_row = src_parent.row() + 1

        # Move under parent before or after if before is None
        elif direction == 1:
            src_row_count = src_parent.rowCount()
            if src_row_count == 1:
                return

            item_row = item.row()
            dst_parent = None
            for row in reversed(range(item_row)):
                _item = src_parent.child(row)
                if not isinstance(_item, AssetItem):
                    continue

                if _item.data(REMOVED_ROLE):
                    continue

                dst_parent = _item
                break

            _next_row = item_row + 1
            if dst_parent is None and _next_row < src_row_count:
                for row in range(_next_row, src_row_count):
                    _item = src_parent.child(row)
                    if not isinstance(_item, AssetItem):
                        continue

                    if _item.data(REMOVED_ROLE):
                        continue

                    dst_parent = _item
                    break

            if dst_parent is None:
                return

            dst_row = dst_parent.rowCount()

        if src_parent is dst_parent:
            return

        if (
            isinstance(item, TaskItem)
            and not isinstance(dst_parent, AssetItem)
        ):
            return

        dst_parent_index = self.index_from_item(
            dst_parent.row(), 0, dst_parent.parent()
        )

        self.beginMoveRows(
            src_parent_index,
            src_row,
            src_row,
            dst_parent_index,
            dst_row
        )
        src_parent.remove_child(item)
        dst_parent.add_child(item)
        item.set_parent(dst_parent)
        dst_parent.move_to(item, dst_row)

        self.endMoveRows()

        new_index = self.index(dst_row, index.column(), dst_parent_index)
        self.index_moved.emit(new_index)

    def move_horizontal(self, indexes, direction):
        if not indexes:
            return

        if isinstance(indexes, QtCore.QModelIndex):
            indexes = [indexes]

        if len(indexes) == 1:
            self._move_horizontal_single(indexes[0], direction)
            return

        items_by_id = {}
        for index in indexes:
            item_id = index.data(IDENTIFIER_ROLE)
            item = self._items_by_id[item_id]
            if isinstance(item, (RootItem, ProjectItem)):
                continue

            if (
                direction == -1
                and isinstance(item.parent(), (RootItem, ProjectItem))
            ):
                continue

            items_by_id[item_id] = item

        if not items_by_id:
            return

        parents_by_id = {}
        items_ids_by_parent_id = collections.defaultdict(set)
        skip_ids = set(items_by_id.keys())
        for item_id, item in tuple(items_by_id.items()):
            item_parent = item.parent()

            parent_ids = set()
            skip_item = False
            parent = item_parent
            while parent is not None:
                if parent.id in skip_ids:
                    skip_item = True
                    skip_ids |= parent_ids
                    break
                parent_ids.add(parent.id)
                parent = parent.parent()

            if skip_item:
                items_by_id.pop(item_id)
            else:
                parents_by_id[item_parent.id] = item_parent
                items_ids_by_parent_id[item_parent.id].add(item_id)

        if direction == 1:
            for parent_id, parent in parents_by_id.items():
                items_ids = items_ids_by_parent_id[parent_id]
                if len(items_ids) == parent.rowCount():
                    for item_id in items_ids:
                        items_by_id.pop(item_id)

        items = tuple(items_by_id.values())
        if direction == -1:
            items = reversed(items)

        for item in items:
            index = self.index_for_item(item)
            self._move_horizontal_single(index, direction)

    def _move_vertical_single(self, index, direction):
        if not index.isValid():
            return

        item_id = index.data(IDENTIFIER_ROLE)
        item = self._items_by_id[item_id]
        if isinstance(item, (RootItem, ProjectItem)):
            return

        if item.data(REMOVED_ROLE):
            return

        if (
            isinstance(item, AssetItem)
            and not item.data(HIERARCHY_CHANGE_ABLE_ROLE)
        ):
            return

        if abs(direction) != 1:
            return

        src_parent = item.parent()
        if not isinstance(src_parent, AssetItem):
            return

        src_parent_index = self.index_from_item(
            src_parent.row(), 0, src_parent.parent()
        )
        source_row = item.row()

        parent_items = []
        parent = src_parent
        while True:
            parent = parent.parent()
            parent_items.insert(0, parent)
            if isinstance(parent, ProjectItem):
                break

        dst_parent = None
        # Down
        if direction == 1:
            current_idxs = []
            current_max_idxs = []
            for parent_item in parent_items:
                current_max_idxs.append(parent_item.rowCount())
                if not isinstance(parent_item, ProjectItem):
                    current_idxs.append(parent_item.row())
            current_idxs.append(src_parent.row())
            indexes_len = len(current_idxs)

            while True:
                def _update_parents(idx, top=True):
                    if idx < 0:
                        return False

                    if current_max_idxs[idx] == current_idxs[idx]:
                        if not _update_parents(idx - 1, False):
                            return False

                        parent = parent_items[idx]
                        row_count = 0
                        if parent is not None:
                            row_count = parent.rowCount()
                        current_max_idxs[idx] = row_count
                        current_idxs[idx] = 0
                        return True

                    if top:
                        return True

                    current_idxs[idx] += 1
                    parent_item = parent_items[idx]
                    new_item = parent_item.child(current_idxs[idx])
                    parent_items[idx + 1] = new_item

                    return True

                updated = _update_parents(indexes_len - 1)
                if not updated:
                    return

                start = current_idxs[-1]
                end = current_max_idxs[-1]
                current_idxs[-1] = current_max_idxs[-1]
                parent = parent_items[-1]
                for row in range(start, end):
                    child_item = parent.child(row)
                    if (
                        child_item is src_parent
                        or child_item.data(REMOVED_ROLE)
                        or not isinstance(child_item, AssetItem)
                    ):
                        continue

                    dst_parent = child_item
                    destination_row = 0
                    break

                if dst_parent is not None:
                    break

        # Up
        elif direction == -1:
            current_idxs = []
            for parent_item in parent_items:
                if not isinstance(parent_item, ProjectItem):
                    current_idxs.append(parent_item.row())
            current_idxs.append(src_parent.row())

            max_idxs = [0 for _ in current_idxs]
            indexes_len = len(current_idxs)

            while True:
                if current_idxs == max_idxs:
                    return

                def _update_parents(_current_idx, top=True):
                    if _current_idx < 0:
                        return False

                    if current_idxs[_current_idx] == 0:
                        if not _update_parents(_current_idx - 1, False):
                            return False

                        parent = parent_items[_current_idx]
                        row_count = 0
                        if parent is not None:
                            row_count = parent.rowCount()
                        current_idxs[_current_idx] = row_count
                        return True
                    if top:
                        return True

                    current_idxs[_current_idx] -= 1
                    parent_item = parent_items[_current_idx]
                    new_item = parent_item.child(current_idxs[_current_idx])
                    parent_items[_current_idx + 1] = new_item

                    return True

                updated = _update_parents(indexes_len - 1)
                if not updated:
                    return

                parent_item = parent_items[-1]
                row_count = current_idxs[-1]
                current_idxs[-1] = 0
                for row in reversed(range(row_count)):
                    child_item = parent_item.child(row)
                    if (
                        child_item is src_parent
                        or child_item.data(REMOVED_ROLE)
                        or not isinstance(child_item, AssetItem)
                    ):
                        continue

                    dst_parent = child_item
                    destination_row = dst_parent.rowCount()
                    break

                if dst_parent is not None:
                    break

        if dst_parent is None:
            return

        dst_parent_index = self.index_from_item(
            dst_parent.row(), 0, dst_parent.parent()
        )

        self.beginMoveRows(
            src_parent_index,
            source_row,
            source_row,
            dst_parent_index,
            destination_row
        )

        if src_parent is dst_parent:
            dst_parent.move_to(item, destination_row)

        else:
            src_parent.remove_child(item)
            dst_parent.add_child(item)
            item.set_parent(dst_parent)
            dst_parent.move_to(item, destination_row)

        self.endMoveRows()

        new_index = self.index(
            destination_row, index.column(), dst_parent_index
        )
        self.index_moved.emit(new_index)

    def move_vertical(self, indexes, direction):
        """Move item vertically in model to matching parent if possible.

        If passed indexes contain items that has parent<->child relation at any
        hierarchy level only the top parent is actually moved.

        Example (items marked with star are passed in `indexes`):
        - shots*
            - ep01
                - ep01_sh0010*
                - ep01_sh0020*
        In this case only `shots` item will be moved vertically and
        both "ep01_sh0010" "ep01_sh0020" will stay as children of "ep01".

        Args:
            indexes(list[QModelIndex]): Indexes that should be moved
                vertically.
            direction(int): Which way will be moved -1 or 1 to determine.
        """
        if not indexes:
            return

        # Convert single index to list of indexes
        if isinstance(indexes, QtCore.QModelIndex):
            indexes = [indexes]

        # Just process single index
        if len(indexes) == 1:
            self._move_vertical_single(indexes[0], direction)
            return

        items_by_id = {}
        for index in indexes:
            item_id = index.data(IDENTIFIER_ROLE)
            items_by_id[item_id] = self._items_by_id[item_id]

        skip_ids = set(items_by_id.keys())
        for item_id, item in tuple(items_by_id.items()):
            parent = item.parent()
            parent_ids = set()
            skip_item = False
            while parent is not None:
                if parent.id in skip_ids:
                    skip_item = True
                    skip_ids |= parent_ids
                    break
                parent_ids.add(parent.id)
                parent = parent.parent()

            if skip_item:
                items_by_id.pop(item_id)

        items = tuple(items_by_id.values())
        if direction == 1:
            items = reversed(items)

        for item in items:
            index = self.index_for_item(item)
            self._move_vertical_single(index, direction)

    def child_removed(self, child):
        """Callback for removed child."""
        self._items_by_id.pop(child.id, None)

    def column_name(self, column):
        """Return column key by index"""
        if column < len(self.columns):
            return self.columns[column]
        return None

    def clear(self):
        """Reset model."""
        self.beginResetModel()
        self._reset_root_item()
        self.endResetModel()

    def save(self):
        """Save all changes from current project manager session.

        Will create new asset documents, update existing and asset documents
        marked for deletion are removed from mongo if has published content or
        their type is changed to `archived_asset` to not loose their data.
        """
        # Check if all items are valid before save
        all_valid = True
        for item in self._items_by_id.values():
            if not item.is_valid:
                all_valid = False
                break

        if not all_valid:
            return

        # Check project item and do not save without it
        project_item = None
        for _project_item in self._root_item.children():
            project_item = _project_item

        if not project_item:
            return

        project_name = project_item.name
        project_col = self.dbcon.database[project_name]

        # Process asset items per one hierarchical level.
        # - new assets are inserted per one parent
        # - update and delete data are stored and processed at once at the end
        to_process = collections.deque()
        to_process.append(project_item)

        bulk_writes = []
        while to_process:
            parent = to_process.popleft()
            insert_list = []
            for item in parent.children():
                if not isinstance(item, AssetItem):
                    continue

                to_process.append(item)

                if item.is_new:
                    insert_list.append(item)

                elif item.data(REMOVED_ROLE):
                    if item.data(HIERARCHY_CHANGE_ABLE_ROLE):
                        bulk_writes.append(DeleteOne(
                            {"_id": item.asset_id}
                        ))
                    else:
                        bulk_writes.append(UpdateOne(
                            {"_id": item.asset_id},
                            {"$set": {"type": "archived_asset"}}
                        ))

                else:
                    update_data = item.update_data()
                    if update_data:
                        bulk_writes.append(UpdateOne(
                            {"_id": item.asset_id},
                            update_data
                        ))

            if insert_list:
                new_docs = []
                for item in insert_list:
                    new_docs.append(item.to_doc())

                result = project_col.insert_many(new_docs)
                for idx, mongo_id in enumerate(result.inserted_ids):
                    insert_list[idx].mongo_id = mongo_id

        if bulk_writes:
            project_col.bulk_write(bulk_writes)

        self.refresh_project()

    def copy_mime_data(self, indexes):
        items = []
        processed_ids = set()
        for index in indexes:
            if not index.isValid():
                continue
            item_id = index.data(IDENTIFIER_ROLE)
            if item_id in processed_ids:
                continue
            processed_ids.add(item_id)
            item = self._items_by_id[item_id]
            items.append(item)

        parent_item = None
        for item in items:
            if not isinstance(item, TaskItem):
                raise ValueError("Can copy only tasks")

            if parent_item is None:
                parent_item = item.parent()
            elif item.parent() is not parent_item:
                raise ValueError("Can copy only tasks from same parent")

        data = []
        for task_item in items:
            data.append(task_item.to_json_data())

        encoded_data = QtCore.QByteArray()
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.WriteOnly)
        stream.writeQString(json.dumps(data))
        mimedata = QtCore.QMimeData()
        mimedata.setData("application/copy_task", encoded_data)
        return mimedata

    def paste_mime_data(self, index, mime_data):
        if not index.isValid():
            return

        item_id = index.data(IDENTIFIER_ROLE)
        item = self._items_by_id[item_id]
        if not isinstance(item, (AssetItem, TaskItem)):
            return

        raw_data = mime_data.data("application/copy_task")
        if isinstance(raw_data, QtCore.QByteArray):
            # Raw data are already QByteArrat and we don't have to load them
            encoded_data = raw_data
        else:
            encoded_data = QtCore.QByteArray.fromRawData(raw_data)
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
        text = stream.readQString()
        try:
            data = json.loads(text)
        except Exception:
            data = []

        if not data:
            return

        if isinstance(item, TaskItem):
            parent = item.parent()
        else:
            parent = item

        for task_item_data in data:
            task_data = {}
            for name, data in task_item_data.items():
                task_data = data
                task_data["name"] = name

            task_item = TaskItem(task_data, True)
            self.add_item(task_item, parent)


class BaseItem:
    """Base item for HierarchyModel.

    Is not meant to be used as real item but as superclass for all items used
    in HierarchyModel.

    TODO cleanup some attributes and methods related only to AssetItem and
    TaskItem.
    """
    columns = []
    # Use `set` for faster result
    editable_columns = set()

    _name_icons = None
    _is_duplicated = False
    item_type = "base"

    _None = object()

    def __init__(self, data=None):
        self._id = uuid4()
        self._children = list()
        self._parent = None

        self._data = {
            key: None
            for key in self.columns
        }
        self._global_data = {}
        self._source_data = data
        if data:
            for key, value in data.items():
                if key in self.columns:
                    self._data[key] = value

    def name_icon(self):
        """Icon shown next to name.

        Item must imlpement this method to change it.
        """
        return None

    @property
    def is_valid(self):
        return not self._is_duplicated

    def model(self):
        return self._parent.model()

    def move_to(self, item, row):
        idx = self._children.index(item)
        if idx == row:
            return

        self._children.pop(idx)
        self._children.insert(row, item)

    def _get_global_data(self, role):
        """Global data getter without column specification."""
        if role == ITEM_TYPE_ROLE:
            return self.item_type

        if role == IDENTIFIER_ROLE:
            return self._id

        if role == DUPLICATED_ROLE:
            return self._is_duplicated

        if role == REMOVED_ROLE:
            return False

        return self._global_data.get(role, self._None)

    def _set_global_data(self, value, role):
        self._global_data[role] = value
        return True

    def data(self, role, key=None):
        value = self._get_global_data(role)
        if value is not self._None:
            return value

        if key not in self.columns:
            return None

        if role == QtCore.Qt.ForegroundRole:
            if key == "name" and not self.is_valid:
                return ResourceCache.colors["warning"]
            return None

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            value = self._data[key]
            if value is None:
                value = self.parent().data(role, key)
            return value

        if role == QtCore.Qt.DecorationRole and key == "name":
            return self.name_icon()
        return None

    def setData(self, value, role, key=None):
        if role == DUPLICATED_ROLE:
            if value == self._is_duplicated:
                return False

            self._is_duplicated = value
            return True

        if role == QtCore.Qt.EditRole:
            if key in self.editable_columns:
                self._data[key] = value
                # must return true if successful
                return True

        return self._set_global_data(value, role)

    @property
    def id(self):
        return self._id

    @property
    def is_new(self):
        return False

    def rowCount(self):
        return len(self._children)

    def child(self, row):
        if -1 < row < self.rowCount():
            return self._children[row]
        return None

    def children(self):
        return self._children

    def child_row(self, child):
        if child not in self._children:
            return -1
        return self._children.index(child)

    def parent(self):
        return self._parent

    def set_parent(self, parent):
        if parent is self._parent:
            return

        if self._parent:
            self._parent.remove_child(self)
        self._parent = parent

    def row(self):
        if self._parent is not None:
            return self._parent.child_row(self)
        return -1

    def add_child(self, item, row=None):
        if item in self._children:
            return

        row_count = self.rowCount()
        if row is None or row == row_count:
            self._children.append(item)
            return

        if row > row_count or row < 0:
            raise ValueError(
                "Invalid row number {} expected range 0 - {}".format(
                    row, row_count
                )
            )

        self._children.insert(row, item)

    def remove_child(self, item):
        if item in self._children:
            self._children.remove(item)

    def flags(self, key):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if key in self.editable_columns:
            flags |= QtCore.Qt.ItemIsEditable
        return flags


class RootItem(BaseItem):
    """Invisible root item used as base item for model."""
    item_type = "root"

    def __init__(self, model):
        super(RootItem, self).__init__()
        self._model = model

    def model(self):
        return self._model

    def flags(self, *args, **kwargs):
        return QtCore.Qt.NoItemFlags


class ProjectItem(BaseItem):
    """Item representing project document in Mongo.

    Item is used only to read it's data. It is not possible to modify them.
    """
    item_type = "project"

    columns = {
        "name",
        "type",
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight",
        "handleStart",
        "handleEnd",
        "clipIn",
        "clipOut",
        "pixelAspect",
        "tools_env",
    }
    query_projection = {
        "_id": 1,
        "name": 1,
        "type": 1,

        "data.frameStart": 1,
        "data.frameEnd": 1,
        "data.fps": 1,
        "data.resolutionWidth": 1,
        "data.resolutionHeight": 1,
        "data.handleStart": 1,
        "data.handleEnd": 1,
        "data.clipIn": 1,
        "data.clipOut": 1,
        "data.pixelAspect": 1,
        "data.tools_env": 1
    }

    def __init__(self, project_doc):
        self._mongo_id = project_doc["_id"]

        data = self.data_from_doc(project_doc)
        super(ProjectItem, self).__init__(data)

    @property
    def project_id(self):
        """Project Mongo ID."""
        return self._mongo_id

    @property
    def asset_id(self):
        """Should not be implemented.

        TODO Remove this method from ProjectItem.
        """
        return None

    @property
    def name(self):
        """Project name"""
        return self._data["name"]

    def child_parents(self):
        """Used by children AssetItems for filling `data.parents` key."""
        return []

    @classmethod
    def data_from_doc(cls, project_doc):
        """Convert document data into item data.

        Project data are used as default value for it's children.
        """
        data = {
            "name": project_doc["name"],
            "type": project_doc["type"]
        }
        doc_data = project_doc.get("data") or {}
        for key in cls.columns:
            if key in data:
                continue

            data[key] = doc_data.get(key)

        return data

    def flags(self, *args, **kwargs):
        """Project is enabled and selectable."""
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


class AssetItem(BaseItem):
    """Item represent asset document.

    Item have ability to set all required and optional data for OpenPype
    workflow. Some of them are not modifiable in specific cases e.g. when asset
    has published content it is not possible to change it's name or parent.
    """
    item_type = "asset"

    columns = {
        "name",
        "type",
        "fps",
        "frameStart",
        "frameEnd",
        "resolutionWidth",
        "resolutionHeight",
        "handleStart",
        "handleEnd",
        "clipIn",
        "clipOut",
        "pixelAspect",
        "tools_env"
    }
    editable_columns = {
        "name",
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight",
        "handleStart",
        "handleEnd",
        "clipIn",
        "clipOut",
        "pixelAspect",
        "tools_env"
    }
    query_projection = {
        "_id": 1,
        "data.tasks": 1,
        "data.visualParent": 1,
        "schema": 1,

        "name": 1,
        "type": 1,
        "data.frameStart": 1,
        "data.frameEnd": 1,
        "data.fps": 1,
        "data.resolutionWidth": 1,
        "data.resolutionHeight": 1,
        "data.handleStart": 1,
        "data.handleEnd": 1,
        "data.clipIn": 1,
        "data.clipOut": 1,
        "data.pixelAspect": 1,
        "data.tools_env": 1
    }

    def __init__(self, asset_doc):
        if not asset_doc:
            asset_doc = {}
        self.mongo_id = asset_doc.get("_id")
        self._project_id = None
        self._edited_columns = {
            column_name: False
            for column_name in self.editable_columns
        }

        # Item data
        self._hierarchy_changes_enabled = True
        self._removed = False

        # Task children duplication variables
        self._task_items_by_name = collections.defaultdict(list)
        self._task_name_by_item_id = {}
        self._duplicated_task_names = set()

        # Copy of original document
        self._origin_asset_doc = copy.deepcopy(asset_doc)

        data = self.data_from_doc(asset_doc)

        self._origin_data = copy.deepcopy(data)

        super(AssetItem, self).__init__(data)

    @property
    def project_id(self):
        """Access to project "parent" id which is always set."""
        if self._project_id is None:
            self._project_id = self.parent().project_id
        return self._project_id

    @property
    def asset_id(self):
        """Property access to mongo id."""
        return self.mongo_id

    @property
    def is_new(self):
        """Item was created during current project manager session."""
        return self.asset_id is None

    @property
    def is_valid(self):
        """Item is invalid for saving."""
        if self._is_duplicated or not self._data["name"]:
            return False
        return True

    @property
    def name(self):
        """Asset name.

        Returns:
            str: If name is set.
            None: If name is not yet set in that case is AssetItem marked as
                invalid.
        """
        return self._data["name"]

    def child_parents(self):
        """Children AssetItem can use this method to get it's parent names.

        This is used for `data.parents` key on document.
        """
        parents = self.parent().child_parents()
        parents.append(self.name)
        return parents

    def to_doc(self):
        """Convert item to Mongo document matching asset schema.

        Method does no validate if item is valid or children are valid.

        Returns:
            dict: Document with all related data about asset item also
                contains task children.
        """
        tasks = {}
        for item in self.children():
            if isinstance(item, TaskItem):
                tasks.update(item.to_doc_data())

        doc_data = {
            "parents": self.parent().child_parents(),
            "visualParent": self.parent().asset_id,
            "tasks": tasks
        }
        schema_name = (
            self._origin_asset_doc.get("schema")
            or CURRENT_DOC_SCHEMAS["asset"]
        )

        doc = {
            "name": self.data(QtCore.Qt.EditRole, "name"),
            "type": self.data(QtCore.Qt.EditRole, "type"),
            "schema": schema_name,
            "data": doc_data,
            "parent": self.project_id
        }
        if self.mongo_id:
            doc["_id"] = self.mongo_id

        for key in self._data.keys():
            if key in doc:
                continue
            # Use `data` method to get inherited values
            doc_data[key] = self.data(QtCore.Qt.EditRole, key)

        return doc

    def update_data(self):
        """Changes dictionary ready for Mongo's update.

        Method should be used on save. There is not other usage of this method.

        # Example
        ```python
        {
            "$set": {
                "name": "new_name"
            }
        }
        ```

        Returns:
            dict: May be empty if item was not changed.
        """
        if not self.mongo_id:
            return {}

        document = self.to_doc()

        changes = {}

        for key, value in document.items():
            if key in ("data", "_id"):
                continue

            if (
                key in self._origin_asset_doc
                and self._origin_asset_doc[key] == value
            ):
                continue

            changes[key] = value

        if "data" not in self._origin_asset_doc:
            changes["data"] = document["data"]
        else:
            origin_data = self._origin_asset_doc["data"]

            for key, value in document["data"].items():
                if key in origin_data and origin_data[key] == value:
                    continue
                _key = "data.{}".format(key)
                changes[_key] = value

        if changes:
            return {"$set": changes}
        return {}

    @classmethod
    def data_from_doc(cls, asset_doc):
        """Convert asset document from Mongo to item data."""
        # Minimum required data for cases that it is new AssetItem without doc
        data = {
            "name": None,
            "type": "asset"
        }
        if asset_doc:
            for key in data.keys():
                if key in asset_doc:
                    data[key] = asset_doc[key]

        doc_data = asset_doc.get("data") or {}
        for key in cls.columns:
            if key in data:
                continue

            data[key] = doc_data.get(key)

        return data

    def name_icon(self):
        """Icon shown next to name."""
        if self.__class__._name_icons is None:
            self.__class__._name_icons = ResourceCache.get_icons()["asset"]

        if self._removed:
            icon_type = "removed"
        elif not self.is_valid:
            icon_type = "invalid"
        elif self.is_new:
            icon_type = "new"
        else:
            icon_type = "default"
        return self.__class__._name_icons[icon_type]

    def _get_global_data(self, role):
        """Global data getter without column specification."""
        if role == HIERARCHY_CHANGE_ABLE_ROLE:
            return self._hierarchy_changes_enabled

        if role == REMOVED_ROLE:
            return self._removed

        if role == QtCore.Qt.ToolTipRole:
            name = self.data(QtCore.Qt.EditRole, "name")
            if not name:
                return "Name is not set"

            elif self._is_duplicated:
                return "Duplicated asset name \"{}\"".format(name)
            return None

        return super(AssetItem, self)._get_global_data(role)

    def data(self, role, key=None):
        if role == EDITOR_OPENED_ROLE:
            if key not in self._edited_columns:
                return False
            return self._edited_columns[key]

        if role == QtCore.Qt.DisplayRole and self._edited_columns.get(key):
            return ""

        return super(AssetItem, self).data(role, key)

    def setData(self, value, role, key=None):
        # Store information that column has opened editor
        # - DisplayRole for the column will return empty string
        if role == EDITOR_OPENED_ROLE:
            if key not in self._edited_columns:
                return False
            self._edited_columns[key] = value
            return True

        if role == REMOVED_ROLE:
            self._removed = value
            return True

        # This can be set only on project load (or save)
        if role == HIERARCHY_CHANGE_ABLE_ROLE:
            if self._hierarchy_changes_enabled == value:
                return False
            self._hierarchy_changes_enabled = value
            return True

        # Do not allow to change name if item is marked to not be able do any
        #   hierarchical changes.
        if (
            role == QtCore.Qt.EditRole
            and key == "name"
            and not self._hierarchy_changes_enabled
        ):
            return False
        return super(AssetItem, self).setData(value, role, key)

    def flags(self, key):
        if key == "name":
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            if self._hierarchy_changes_enabled:
                flags |= QtCore.Qt.ItemIsEditable
            return flags
        return super(AssetItem, self).flags(key)

    def _add_task(self, item):
        name = item.data(QtCore.Qt.EditRole, "name").lower()
        item_id = item.data(IDENTIFIER_ROLE)

        self._task_name_by_item_id[item_id] = name
        self._task_items_by_name[name].append(item)
        if len(self._task_items_by_name[name]) > 1:
            self._duplicated_task_names.add(name)
            for _item in self._task_items_by_name[name]:
                _item.setData(True, DUPLICATED_ROLE)
        elif item.data(DUPLICATED_ROLE):
            item.setData(False, DUPLICATED_ROLE)

    def _remove_task(self, item):
        # This method is probably obsolete with changed logic and added
        #   `on_task_remove_state_change` method.
        item_id = item.data(IDENTIFIER_ROLE)
        if item_id not in self._task_name_by_item_id:
            return

        name = self._task_name_by_item_id.pop(item_id)
        self._task_items_by_name[name].remove(item)
        if not self._task_items_by_name[name]:
            self._task_items_by_name.pop(name)

        elif len(self._task_items_by_name[name]) == 1:
            self._duplicated_task_names.remove(name)
            for _item in self._task_items_by_name[name]:
                _item.setData(False, DUPLICATED_ROLE)

    def _rename_task(self, item):
        # Skip processing if item is marked for removing
        # - item is not in any of attributes below
        if item.data(REMOVED_ROLE):
            return

        new_name = item.data(QtCore.Qt.EditRole, "name").lower()
        item_id = item.data(IDENTIFIER_ROLE)
        prev_name = self._task_name_by_item_id[item_id]
        if new_name == prev_name:
            return

        # Remove from previous name mapping
        self._task_items_by_name[prev_name].remove(item)
        if not self._task_items_by_name[prev_name]:
            self._task_items_by_name.pop(prev_name)

        elif len(self._task_items_by_name[prev_name]) == 1:
            self._duplicated_task_names.remove(prev_name)
            for _item in self._task_items_by_name[prev_name]:
                _item.setData(False, DUPLICATED_ROLE)

        # Add to new name mapping
        self._task_items_by_name[new_name].append(item)
        if len(self._task_items_by_name[new_name]) > 1:
            self._duplicated_task_names.add(new_name)
            for _item in self._task_items_by_name[new_name]:
                _item.setData(True, DUPLICATED_ROLE)
        else:
            item.setData(False, DUPLICATED_ROLE)

        self._task_name_by_item_id[item_id] = new_name

    def on_task_name_change(self, task_item):
        """Method called from TaskItem children on name change.

        Helps to handle duplicated task name validations.
        """

        self._rename_task(task_item)

    def on_task_remove_state_change(self, task_item):
        """Method called from children TaskItem to handle name duplications.

        Method is called when TaskItem children is marked for deletion or
        deletion was reversed.

        Name is removed/added to task item mapping attribute and removed/added
        to `_task_items_by_name` used for determination of duplicated tasks.
        """
        is_removed = task_item.data(REMOVED_ROLE)
        item_id = task_item.data(IDENTIFIER_ROLE)
        if is_removed:
            name = self._task_name_by_item_id.pop(item_id)
            self._task_items_by_name[name].remove(task_item)

        else:
            name = task_item.data(QtCore.Qt.EditRole, "name").lower()
            self._task_name_by_item_id[item_id] = name
            self._task_items_by_name[name].append(task_item)

        # Remove from previous name mapping
        if not self._task_items_by_name[name]:
            self._task_items_by_name.pop(name)

        elif len(self._task_items_by_name[name]) == 1:
            if name in self._duplicated_task_names:
                self._duplicated_task_names.remove(name)
            task_item.setData(False, DUPLICATED_ROLE)

        else:
            self._duplicated_task_names.add(name)
            for _item in self._task_items_by_name[name]:
                _item.setData(True, DUPLICATED_ROLE)

    def add_child(self, item, row=None):
        """Add new children.

        Args:
            item(AssetItem, TaskItem): New added item.
            row(int): Optionally can be passed on which row (index) should be
                children added.
        """
        if item in self._children:
            return

        super(AssetItem, self).add_child(item, row)

        # Call inner method for checking task name duplications
        if isinstance(item, TaskItem):
            self._add_task(item)

    def remove_child(self, item):
        """Remove one of children from AssetItem children.

        Skipped if item is not children of item.

        Args:
            item(AssetItem, TaskItem): Child item.
        """
        if item not in self._children:
            return

        # Call inner method to remove task from registered task name
        #   validations.
        if isinstance(item, TaskItem):
            self._remove_task(item)

        super(AssetItem, self).remove_child(item)


class TaskItem(BaseItem):
    """Item representing Task item on Asset document.

    Always should be AssetItem children and never should have any other
    children.

    It's name value should be validated with it's parent which only knows if
    has same name as other sibling under same parent.
    """

    # String representation of item
    item_type = "task"

    columns = {
        "name",
        "type"
    }
    editable_columns = {
        "name",
        "type"
    }

    def __init__(self, data=None, is_new=None):
        self._removed = False
        if is_new is None:
            is_new = data is None
        self._is_new = is_new
        if data is None:
            data = {}

        self._edited_columns = {
            column_name: False
            for column_name in self.editable_columns
        }
        self._origin_data = copy.deepcopy(data)
        super(TaskItem, self).__init__(data)

    @property
    def is_new(self):
        """Task was created during current project manager session."""
        return self._is_new

    @property
    def is_valid(self):
        """Task valid for saving."""
        if self._is_duplicated or not self._data["type"]:
            return False
        if not self.data(QtCore.Qt.EditRole, "name"):
            return False
        return True

    def name_icon(self):
        """Icon shown next to name."""
        if self.__class__._name_icons is None:
            self.__class__._name_icons = ResourceCache.get_icons()["task"]

        if self._removed:
            icon_type = "removed"
        elif not self.is_valid:
            icon_type = "invalid"
        elif self.is_new:
            icon_type = "new"
        else:
            icon_type = "default"
        return self.__class__._name_icons[icon_type]

    def add_child(self, item, row=None):
        """Reimplement `add_child` to avoid adding items under task."""
        raise AssertionError("BUG: Can't add children to Task")

    def _get_global_data(self, role):
        """Global data getter without column specification."""
        if role == REMOVED_ROLE:
            return self._removed

        if role == QtCore.Qt.ToolTipRole:
            if not self._data["type"]:
                return "Type is not set"

            name = self.data(QtCore.Qt.EditRole, "name")
            if not name:
                return "Name is not set"

            elif self._is_duplicated:
                return "Duplicated task name \"{}".format(name)
            return None

        return super(TaskItem, self)._get_global_data(role)

    def to_doc_data(self):
        """Data for Asset document.

        Returns:
            dict: May be empty if task is marked as removed or with single key
                dict with name as key and task data as value.
        """
        if self._removed:
            return {}
        data = copy.deepcopy(self._data)
        data.pop("name")
        name = self.data(QtCore.Qt.EditRole, "name")
        return {
            name: data
        }

    def data(self, role, key=None):
        if role == EDITOR_OPENED_ROLE:
            if key not in self._edited_columns:
                return False
            return self._edited_columns[key]

        # Return empty string if column is edited
        if role == QtCore.Qt.DisplayRole and self._edited_columns.get(key):
            return ""

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if key == "type":
                return self._data["type"]

            # Always require task type filled
            if key == "name":
                if not self._data["type"]:
                    if role == QtCore.Qt.DisplayRole:
                        return "< Select Type >"
                    if role == QtCore.Qt.EditRole:
                        return ""
                else:
                    return self._data[key] or self._data["type"]

        return super(TaskItem, self).data(role, key)

    def setData(self, value, role, key=None):
        # Store information that item on a column is edited
        #   - DisplayRole will return empty string in that case
        if role == EDITOR_OPENED_ROLE:
            if key not in self._edited_columns:
                return False
            self._edited_columns[key] = value
            return True

        if role == REMOVED_ROLE:
            # Skip value change if is same as already set value
            if value == self._removed:
                return False
            self._removed = value
            self.parent().on_task_remove_state_change(self)
            return True

        # Convert empty string to None on EditRole
        if (
            role == QtCore.Qt.EditRole
            and key == "name"
            and not value
        ):
            value = None

        result = super(TaskItem, self).setData(value, role, key)

        if role == QtCore.Qt.EditRole:
            # Trigger task name change of parent AssetItem
            if (
                key == "name"
                or (key == "type" and not self._data["name"])
            ):
                self.parent().on_task_name_change(self)

        return result

    def to_json_data(self):
        """Convert json data without parent reference.

        Method used for mime data on copy/paste
        """
        return self.to_doc_data()
