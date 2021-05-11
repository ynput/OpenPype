import collections
import copy
from queue import Queue
from uuid import uuid4

from .constants import (
    IDENTIFIER_ROLE,
    DUPLICATED_ROLE,
    HIERARCHY_CHANGE_ABLE_ROLE,
    REMOVED_ROLE
)
from pymongo import UpdateOne
from avalon.vendor import qtawesome
from Qt import QtCore, QtGui


class ProjectModel(QtGui.QStandardItemModel):
    project_changed = QtCore.Signal()

    def __init__(self, dbcon, *args, **kwargs):
        self.dbcon = dbcon

        self._project_names = set()

        super(ProjectModel, self).__init__(*args, **kwargs)

    def refresh(self):
        self.dbcon.Session["AVALON_PROJECT"] = None

        project_items = []
        database = self.dbcon.database
        project_names = set()
        for project_name in database.collection_names():
            # Each collection will have exactly one project document
            project_doc = database[project_name].find_one(
                {"type": "project"},
                {"name": 1}
            )
            if not project_doc:
                continue

            project_name = project_doc.get("name")
            if project_name:
                project_names.add(project_name)
                project_items.append(QtGui.QStandardItem(project_name))

        self.clear()

        self._project_names = project_names

        self.invisibleRootItem().appendRows(project_items)


class HierarchySelectionModel(QtCore.QItemSelectionModel):
    def setCurrentIndex(self, index, command):
        if index.column() > 0:
            if (
                command & QtCore.QItemSelectionModel.Clear
                and command & QtCore.QItemSelectionModel.Select
            ):
                command = QtCore.QItemSelectionModel.NoUpdate
        super(HierarchySelectionModel, self).setCurrentIndex(index, command)


class HierarchyModel(QtCore.QAbstractItemModel):
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

    def __init__(self, dbcon, parent=None):
        super(HierarchyModel, self).__init__(parent)
        # TODO Reset them on project change
        self._current_project = None
        self._root_item = None
        self._items_by_id = {}
        self._asset_items_by_name = collections.defaultdict(list)
        self.dbcon = dbcon

        self._reset_root_item()

    @property
    def items_by_id(self):
        return self._items_by_id

    def _reset_root_item(self):
        self._root_item = RootItem(self)

    def set_project(self, project_name):
        if self._current_project == project_name:
            return

        self.clear()

        self._current_project = project_name
        if not project_name:
            return

        project_doc = self.dbcon.database[project_name].find_one(
            {"type": "project"},
            ProjectItem.query_projection
        )
        if not project_doc:
            return

        project_item = ProjectItem(project_doc)
        self.add_item(project_item)

        asset_docs = self.dbcon.database[project_name].find(
            {"type": "asset"},
            AssetItem.query_projection
        )
        asset_docs_by_id = {
            asset_doc["_id"]: asset_doc
            for asset_doc in asset_docs
        }

        # Prepare booleans if asset item can be modified (name or hierarchy)
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

        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in asset_docs_by_id.values():
            parent_id = asset_doc["data"]["visualParent"]
            asset_docs_by_parent_id[parent_id].append(asset_doc)

        appending_queue = Queue()
        appending_queue.put((None, project_item))

        asset_items_by_id = {}
        non_modifiable_items = set()
        while not appending_queue.empty():
            parent_id, parent_item = appending_queue.get()
            if parent_id not in asset_docs_by_parent_id:
                continue

            new_items = []
            for asset_doc in asset_docs_by_parent_id[parent_id]:
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
                appending_queue.put((asset_id, new_item))

            self.add_items(new_items, parent_item)

        # Handle Asset's that are not modifiable
        # - pass the information to all it's parents
        non_modifiable_queue = Queue()
        for item_id in non_modifiable_items:
            non_modifiable_queue.put(item_id)

        while not non_modifiable_queue.empty():
            item_id = non_modifiable_queue.get()
            item = self._items_by_id[item_id]
            item.setData(None, False, HIERARCHY_CHANGE_ABLE_ROLE)

            parent = item.parent()
            if (
                isinstance(parent, AssetItem)
                and parent.id not in non_modifiable_items
            ):
                non_modifiable_items.add(parent.id)
                non_modifiable_queue.put(parent.id)

        # Add task items
        for asset_id, asset_item in asset_items_by_id.items():
            asset_doc = asset_docs_by_id[asset_id]
            asset_tasks = asset_doc["data"]["tasks"]
            if not asset_tasks:
                continue

            task_items = []
            for task_name, task_data in asset_tasks.items():
                _task_data = copy.deepcopy(task_data)
                _task_data["name"] = task_name
                task_item = TaskItem(_task_data)
                task_items.append(task_item)
            self.add_items(task_items, asset_item)

    def rowCount(self, parent=None):
        if parent is None or not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.rowCount()

    def columnCount(self, *args, **kwargs):
        return self.columns_len

    def data(self, index, role):
        if not index.isValid():
            return None

        column = index.column()
        key = self.columns[column]

        item = index.internalPointer()
        return item.data(key, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False

        item = index.internalPointer()
        column = index.column()
        key = self.columns[column]
        if (
            key == "name"
            and role in (QtCore.Qt.EditRole, QtCore.Qt.DisplayRole)
        ):
            self._rename_asset(item, value)

        result = item.setData(key, value, role)
        if result:
            self.dataChanged.emit(index, index, [role])

        return result

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section < self.columnCount():
                return self.column_labels[section]

        return super(HierarchyModel, self).headerData(
            section, orientation, role
        )

    def flags(self, index):
        item = index.internalPointer()
        column = index.column()
        key = self.columns[column]
        return item.flags(key)

    def parent(self, index=None):
        if not index.isValid():
            return QtCore.QModelIndex()

        item = index.internalPointer()
        parent_item = item.parent()

        # If it has no parents we return invalid
        if not parent_item or parent_item is self._root_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def index(self, row, column, parent=None):
        """Return index for row/column under parent"""
        parent_item = None
        if parent is not None and parent.isValid():
            parent_item = parent.internalPointer()

        return self.index_from_item(row, column, parent_item)

    def index_for_item(self, item, column=0):
        return self.index_from_item(
            item.row(), column, item.parent()
        )

    def index_from_item(self, row, column, parent=None):
        if parent is None:
            parent = self._root_item

        child_item = parent.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)

        return QtCore.QModelIndex()

    def add_new_asset(self, source_index):
        item_id = source_index.data(IDENTIFIER_ROLE)
        item = self.items_by_id[item_id]

        new_row = None
        name = None
        asset_data = {}
        if isinstance(item, (RootItem, ProjectItem)):
            name = "ep"
            parent = item
        else:
            parent = item.parent()
            new_row = item.row() + 1

        if name:
            asset_data["name"] = name

        new_child = AssetItem(asset_data)

        result = self.add_item(new_child, parent, new_row)
        if result is not None:
            self._validate_asset_duplicity(name)

        return result

    def add_new_task(self, parent_index):
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
        if parent is None:
            parent = self._root_item

        if parent.data(None, REMOVED_ROLE):
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
                name = item.data("name", QtCore.Qt.DisplayRole)
                self._asset_items_by_name[name].append(item)

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
        result = self.add_items([item], parent, row)
        if result:
            return result[0]
        return None

    def remove_index(self, index):
        if not index.isValid():
            return

        item = index.internalPointer()

        if isinstance(item, (RootItem, ProjectItem)):
            return

        parent = item.parent()

        all_descendants = collections.defaultdict(dict)
        all_descendants[parent.id][item.id] = item

        def _fill_children(_all_descendants, cur_item, parent_item=None):
            if parent_item is not None:
                _all_descendants[parent_item.id][cur_item.id] = cur_item

            if isinstance(cur_item, TaskItem):
                task_removed = True
                cur_item.setData(None, task_removed, REMOVED_ROLE)
                return task_removed

            remove_item = cur_item.data(None, HIERARCHY_CHANGE_ABLE_ROLE)
            for row in range(cur_item.rowCount()):
                child_item = cur_item.child(row)
                if not _fill_children(_all_descendants, child_item, cur_item):
                    remove_item = False

            if remove_item:
                cur_item.setData(None, True, REMOVED_ROLE)
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

                parent_item = self._items_by_id[parent_id]
                row_ranges = []
                start_row = end_row = None
                chilren_by_row = {}
                for row in range(parent_item.rowCount()):
                    child_item = parent_item.child(row)
                    child_id = child_item.id
                    if child_id not in children:
                        continue

                    chilren_by_row[row] = child_item
                    children.pop(child_item.id)

                    remove_item = child_item.data(None, REMOVED_ROLE)
                    if not remove_item or not child_item.is_new:
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

                parent_index = None
                for start, end in row_ranges:
                    if parent_index is None:
                        parent_index = self.index_for_item(parent_item)

                    self.beginRemoveRows(parent_index, start, end)

                    for idx in range(start, end + 1):
                        child_item = chilren_by_row[idx]
                        # Force name validation
                        if isinstance(child_item, AssetItem):
                            self._rename_asset(child_item, None)
                        child_item.set_parent(None)
                        self._items_by_id.pop(child_item.id)

                    self.endRemoveRows()

        for item in modified_children:
            s_index = self.index_for_item(item)
            e_index = self.index_for_item(item, column=self.columns_len - 1)
            self.dataChanged.emit(s_index, e_index, [QtCore.Qt.BackgroundRole])

    def _rename_asset(self, asset_item, new_name):
        if not isinstance(asset_item, AssetItem):
            return

        prev_name = asset_item.data("name", QtCore.Qt.DisplayRole)
        if prev_name == new_name:
            return

        self._asset_items_by_name[prev_name].remove(asset_item)

        self._validate_asset_duplicity(prev_name)

        if new_name is None:
            return
        self._asset_items_by_name[new_name].append(asset_item)

        self._validate_asset_duplicity(new_name)

    def _validate_asset_duplicity(self, name):
        if name not in self._asset_items_by_name:
            return

        items = self._asset_items_by_name[name]
        if not items:
            self._asset_items_by_name.pop(name)

        elif len(items) == 1:
            index = self.index_for_item(items[0])
            self.setData(index, False, DUPLICATED_ROLE)
        else:
            for item in items:
                index = self.index_for_item(item)
                self.setData(index, True, DUPLICATED_ROLE)

    def _move_vertical_single(self, index, direction):
        if not index.isValid():
            return

        item_id = index.data(IDENTIFIER_ROLE)
        if item_id is None:
            return

        item = self._items_by_id[item_id]
        if isinstance(item, (RootItem, ProjectItem)):
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
        dst_parent_index = None

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
                if row == item_row:
                    continue
                _item = src_parent.child(row)
                if not isinstance(_item, TaskItem):
                    dst_parent = _item
                    break

            if dst_parent is None:
                for row in range(item_row + 1, src_row_count + 2):
                    _item = src_parent.child(row)
                    if not isinstance(_item, TaskItem):
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

        if dst_parent_index is None:
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

        self.index_moved.emit(index)

    def move_vertical(self, indexes, direction):
        if not indexes:
            return

        if isinstance(indexes, QtCore.QModelIndex):
            indexes = [indexes]

        if len(indexes) == 1:
            self._move_vertical_single(indexes[0], direction)
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
            self._move_vertical_single(index, direction)

    def _move_horizontal_single(self, index, direction):
        if not index.isValid():
            return

        item_id = index.data(IDENTIFIER_ROLE)
        item = self._items_by_id[item_id]
        if isinstance(item, (RootItem, ProjectItem)):
            return

        if abs(direction) != 1:
            return

        src_parent = item.parent()
        src_parent_index = self.index_from_item(
            src_parent.row(), 0, src_parent.parent()
        )
        source_row = item.row()

        dst_parent = None
        dst_parent_index = None
        destination_row = None
        _destination_row = None
        # Down
        if direction == 1:
            if source_row < src_parent.rowCount() - 1:
                dst_parent_index = src_parent_index
                dst_parent = src_parent
                destination_row = source_row + 1
                # This row is not row number after moving but before moving
                _destination_row = destination_row + 1
            else:
                destination_row = 0
                parent_parent = src_parent.parent()
                if not parent_parent:
                    return

                new_parent = parent_parent.child(src_parent.row() + 1)
                if not new_parent:
                    return
                dst_parent = new_parent

        # Up
        elif direction == -1:
            if source_row > 0:
                dst_parent_index = src_parent_index
                dst_parent = src_parent
                destination_row = source_row - 1
            else:
                parent_parent = src_parent.parent()
                if not parent_parent:
                    return

                previous_parent = parent_parent.child(src_parent.row() - 1)
                if not previous_parent:
                    return
                dst_parent = previous_parent
                destination_row = previous_parent.rowCount()

        if dst_parent_index is None:
            dst_parent_index = self.index_from_item(
                dst_parent.row(), 0, dst_parent.parent()
            )

        if _destination_row is None:
            _destination_row = destination_row

        self.beginMoveRows(
            src_parent_index,
            source_row,
            source_row,
            dst_parent_index,
            _destination_row
        )

        if src_parent is dst_parent:
            dst_parent.move_to(item, destination_row)

        else:
            src_parent.remove_child(item)
            dst_parent.add_child(item)
            item.set_parent(dst_parent)
            dst_parent.move_to(item, destination_row)

        self.endMoveRows()

        self.index_moved.emit(index)

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
            self._move_horizontal_single(index, direction)

    def child_removed(self, child):
        self._items_by_id.pop(child.id, None)

    def column_name(self, column):
        """Return column key by index"""
        if column < len(self.columns):
            return self.columns[column]
        return None

    def clear(self):
        self.beginResetModel()
        self._reset_root_item()
        self.endResetModel()

    def save(self):
        all_valid = True
        for item in self._items_by_id.values():
            if not item.is_valid:
                all_valid = False
                break

        if not all_valid:
            return

        project_item = None
        for _project_item in self._root_item.children():
            project_item = _project_item

        if not project_item:
            return

        project_name = project_item.name
        project_col = self.dbcon.database[project_name]

        to_process = Queue()
        to_process.put(project_item)

        update_list = []
        while not to_process.empty():
            parent = to_process.get()
            insert_list = []
            for item in parent.children():
                if not isinstance(item, AssetItem):
                    continue

                to_process.put(item)

                if item.is_new:
                    insert_list.append(item)
                    continue

                update_data = item.update_data()
                if update_data:
                    update_list.append(UpdateOne(
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

        if update_list:
            project_col.bulk_write(update_list)


class BaseItem:
    columns = []
    # Use `set` for faster result
    editable_columns = set()

    _name_icon = None
    _is_duplicated = False

    _None = object()

    def __init__(self, data=None):
        self._id = uuid4()
        self._children = list()
        self._parent = None

        self._data = {
            key: None
            for key in self.columns
        }
        self._source_data = data
        if data:
            for key, value in data.items():
                if key in self.columns:
                    self._data[key] = value

    @classmethod
    def name_icon(cls):
        return cls._name_icon

    @property
    def is_valid(self):
        return not self._is_duplicated

    def model(self):
        return self._parent.model

    def move_to(self, item, row):
        idx = self._children.index(item)
        if idx == row:
            return

        self._children.pop(idx)
        self._children.insert(row, item)

    def _global_data(self, role):
        if role == IDENTIFIER_ROLE:
            return self._id

        if role == DUPLICATED_ROLE:
            return self._is_duplicated

        if role == REMOVED_ROLE:
            return False

        return self._None

    def data(self, key, role):
        value = self._global_data(role)
        if value is not self._None:
            return value

        if key not in self.columns:
            return None

        if role == QtCore.Qt.ForegroundRole:
            if self._is_duplicated and key == "name":
                return QtGui.QColor(255, 0, 0)
            return None

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            value = self._data[key]
            if value is None:
                value = self.parent().data(key, role)
            return value

        if role == QtCore.Qt.DecorationRole and key == "name":
            return self.name_icon()
        return None

    def setData(self, key, value, role):
        if role == DUPLICATED_ROLE:
            if value == self._is_duplicated:
                return False

            self._is_duplicated = value
            return True

        if role == QtCore.Qt.EditRole:
            if key not in self.editable_columns:
                return False

            self._data[key] = value
            # must return true if successful
            return True

        return False

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
    def __init__(self, model):
        super(RootItem, self).__init__()
        self._model = model

    def model(self):
        return self._model

    def flags(self, *args, **kwargs):
        return QtCore.Qt.NoItemFlags


class ProjectItem(BaseItem):
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
        return self._mongo_id

    @property
    def asset_id(self):
        return None

    @property
    def name(self):
        return self._data["name"]

    def child_parents(self):
        return []

    @classmethod
    def data_from_doc(cls, project_doc):
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
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


class AssetItem(BaseItem):
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
        super(AssetItem, self).__init__(data)

    @property
    def project_id(self):
        if self._project_id is None:
            self._project_id = self.parent().project_id
        return self._project_id

    @property
    def asset_id(self):
        return self.mongo_id

    @property
    def is_new(self):
        return self.asset_id is None

    @property
    def name(self):
        return self._data["name"]

    def child_parents(self):
        parents = self.parent().child_parents()
        parents.append(self.name)
        return parents

    def to_doc(self):
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
            self._origin_asset_doc.get("schema") or "openpype:asset-3.0"
        )

        doc = {
            "name": self.data("name", QtCore.Qt.DisplayRole),
            "type": self.data("type", QtCore.Qt.DisplayRole),
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
            doc_data[key] = self.data(key, QtCore.Qt.DisplayRole)

        return doc

    def update_data(self):
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

    @classmethod
    def name_icon(cls):
        if cls._name_icon is None:
            cls._name_icon = qtawesome.icon("fa.folder", color="#333333")
        return cls._name_icon

    def _global_data(self, role):
        if role == HIERARCHY_CHANGE_ABLE_ROLE:
            return self._hierarchy_changes_enabled

        if role == REMOVED_ROLE:
            return self._removed

        if role == QtCore.Qt.ToolTipRole and self._is_duplicated:
            return "Asset with name \"{}\" already exists.".format(
                self._data["name"]
            )
        return super(AssetItem, self)._global_data(role)

    def data(self, key, role):
        if role == QtCore.Qt.BackgroundRole:
            if self._removed:
                return QtGui.QColor(255, 0, 0, 127)
            elif self.is_new:
                return QtGui.QColor(0, 255, 0, 127)

        return super(AssetItem, self).data(key, role)

    def setData(self, key, value, role):
        if role == REMOVED_ROLE:
            self._removed = value
            return True

        if role == HIERARCHY_CHANGE_ABLE_ROLE:
            if self._hierarchy_changes_enabled == value:
                return False
            self._hierarchy_changes_enabled = value
            return True

        if (
            role == QtCore.Qt.EditRole
            and key == "name"
            and not self._hierarchy_changes_enabled
        ):
            return False
        return super(AssetItem, self).setData(key, value, role)

    def flags(self, key):
        if key == "name":
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            if self._hierarchy_changes_enabled:
                flags |= QtCore.Qt.ItemIsEditable
            return flags
        return super(AssetItem, self).flags(key)

    def _add_task(self, item):
        name = item.data("name", QtCore.Qt.DisplayRole).lower()
        item_id = item.data(None, IDENTIFIER_ROLE)

        self._task_name_by_item_id[item_id] = name
        self._task_items_by_name[name].append(item)
        if len(self._task_items_by_name[name]) > 1:
            self._duplicated_task_names.add(name)
            for _item in self._task_items_by_name[name]:
                _item.setData(None, True, DUPLICATED_ROLE)

    def _remove_task(self, item):
        item_id = item.data(None, IDENTIFIER_ROLE)
        name = self._task_name_by_item_id[item_id]

        self._task_name_by_item_id.pop(item_id)
        self._task_items_by_name[name].append(item)
        if not self._task_items_by_name[name]:
            self._task_items_by_name.pop(name)

        elif len(self._task_items_by_name[name]) == 1:
            self._duplicated_task_names.remove(name)
            for _item in self._task_items_by_name[name]:
                _item.setData(None, False, DUPLICATED_ROLE)

    def _rename_task(self, item):
        new_name = item.data("name", QtCore.Qt.DisplayRole).lower()
        item_id = item.data(None, IDENTIFIER_ROLE)
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
                _item.setData(None, False, DUPLICATED_ROLE)

        # Add to new name mapping
        self._task_items_by_name[new_name].append(item)
        if len(self._task_items_by_name[new_name]) > 1:
            self._duplicated_task_names.add(new_name)
            for _item in self._task_items_by_name[new_name]:
                _item.setData(None, True, DUPLICATED_ROLE)
        else:
            item.setData(None, False, DUPLICATED_ROLE)

        self._task_name_by_item_id[item_id] = new_name

    def on_task_name_change(self, task_item):
        self._rename_task(task_item)

    def add_child(self, item, row=None):
        if item in self._children:
            return

        super(AssetItem, self).add_child(item, row)

        if isinstance(item, TaskItem):
            self._add_task(item)

    def remove_child(self, item):
        if item not in self._children:
            return

        if isinstance(item, TaskItem):
            self._remove_task(item)

        super(AssetItem, self).remove_child(item)


class TaskItem(BaseItem):
    columns = {
        "name",
        "type"
    }
    editable_columns = {
        "name",
        "type"
    }

    def __init__(self, data=None):
        self._origin_data = copy.deepcopy(data)
        self._removed = False
        if data is None:
            data = {}
        super(TaskItem, self).__init__(data)

    @property
    def is_new(self):
        return self._origin_data is None

    @classmethod
    def name_icon(cls):
        if cls._name_icon is None:
            cls._name_icon = qtawesome.icon("fa.file-o", color="#333333")
        return cls._name_icon

    def add_child(self, item, row=None):
        raise AssertionError("BUG: Can't add children to Task")

    def _global_data(self, role):
        if role == REMOVED_ROLE:
            return self._removed

        if role == QtCore.Qt.ToolTipRole and self._is_duplicated:
            return "Duplicated Task name \"{}\".".format(
                self._data["name"]
            )
        return super(TaskItem, self)._global_data(role)

    def to_doc_data(self):
        data = copy.deepcopy(self._data)
        data.pop("name")
        name = self.data("name", QtCore.Qt.DisplayRole)
        return {
            name: data
        }

    def data(self, key, role):
        if role == QtCore.Qt.BackgroundRole:
            if self._removed:
                return QtGui.QColor(255, 0, 0, 127)

            elif self.is_new:
                return QtGui.QColor(0, 255, 0, 127)

        if (
            role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole)
            and key == "name"
        ):
            return self._data[key] or self._data["type"] or "< Select Type >"
        return super(TaskItem, self).data(key, role)

    def setData(self, key, value, role):
        if role == REMOVED_ROLE:
            self._removed = value
            return True

        result = super(TaskItem, self).setData(key, value, role)

        if (
            key == "name"
            or (key == "type" and self._data["name"] is None)
        ):
            self.parent().on_task_name_change(self)

        return result
