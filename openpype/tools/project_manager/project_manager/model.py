import collections
from queue import Queue
from uuid import uuid4

from .constants import (
    IDENTIFIER_ROLE,
    DUPLICATED_ROLE
)

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
    columns = [
        "name",
        "type",
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight"
    ]
    index_moved = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, dbcon, parent=None):
        super(HierarchyModel, self).__init__(parent)
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
        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in asset_docs:
            parent_id = asset_doc["data"]["visualParent"]
            asset_docs_by_parent_id[parent_id].append(asset_doc)

        appending_queue = Queue()
        appending_queue.put((None, project_item))

        while not appending_queue.empty():
            parent_id, parent_item = appending_queue.get()
            if parent_id not in asset_docs_by_parent_id:
                continue

            new_items = []
            for asset_doc in asset_docs_by_parent_id[parent_id]:
                new_item = AssetItem(asset_doc)
                new_items.append(new_item)
                appending_queue.put((asset_doc["_id"], new_item))

            self.add_items(new_items, parent_item)

    def rowCount(self, parent=None):
        if parent is None or not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.rowCount()

    def columnCount(self, *args, **kwargs):
        return len(self.columns)

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
            if section < len(self.columns):
                return self.columns[section]

        super(HierarchyModel, self).headerData(section, orientation, role)

    def flags(self, index):
        item = index.internalPointer()
        column = index.column()
        key = self.columns[column]
        return item.flags(key)

    def parent(self, index):
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
        if isinstance(item, (RootItem, ProjectItem)):
            name = "eq"
            parent = item
        else:
            name = source_index.data(QtCore.Qt.DisplayRole)
            parent = item.parent()
            new_row = item.row() + 1

        data = {
            "name": name,
            "type": "asset"
        }
        new_child = AssetItem(data)
        self._asset_items_by_name[name].append(new_child)

        result = self.add_item(new_child, parent, new_row)

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

        data = {"name": "task"}
        new_child = TaskItem(data)
        return self.add_item(new_child, parent)

    def add_items(self, items, parent=None, start_row=None):
        if parent is None:
            parent = self._root_item

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
        return self.add_items([item], parent, row)[0]

    def remove_index(self, index):
        if not index.isValid():
            return

        item_id = index.data(IDENTIFIER_ROLE)
        item = self._items_by_id[item_id]
        if isinstance(item, (RootItem, ProjectItem)):
            return

        parent = item.parent()
        all_descendants = collections.defaultdict(dict)
        all_descendants[parent.id][item.id] = item

        row = item.row()
        self.beginRemoveRows(self.index_for_item(parent), row, row)

        todo_queue = Queue()
        todo_queue.put(item)
        while not todo_queue.empty():
            _item = todo_queue.get()
            for row in range(_item.rowCount()):
                child_item = _item.child(row)
                all_descendants[_item.id][child_item.id] = child_item
                todo_queue.put(child_item)

        while all_descendants:
            for parent_id in tuple(all_descendants.keys()):
                children = all_descendants[parent_id]
                if not children:
                    all_descendants.pop(parent_id)
                    continue

                for child_id in tuple(children.keys()):
                    child_item = children[child_id]
                    if child_id in all_descendants:
                        continue

                    if isinstance(child_item, AssetItem):
                        self._rename_asset(child_item, None)
                    children.pop(child_id)
                    child_item.set_parent(None)
                    self._items_by_id.pop(child_id)

        self.endRemoveRows()

    def _rename_asset(self, asset_item, new_name):
        if not isinstance(asset_item, AssetItem):
            return

        prev_name = asset_item.data("name", QtCore.Qt.DisplayRole)
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


class BaseItem:
    columns = []
    # Use `set` for faster result
    editable_columns = set()

    _name_icon = None
    _is_duplicated = False

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

    def model(self):
        return self._parent.model

    def move_to(self, item, row):
        idx = self._children.index(item)
        if idx == row:
            return

        self._children.pop(idx)
        self._children.insert(row, item)

    def data(self, key, role):
        if role == IDENTIFIER_ROLE:
            return self._id

        if role == DUPLICATED_ROLE:
            return self._is_duplicated

        if role == QtCore.Qt.ToolTipRole:
            if self._is_duplicated:
                return "Asset with name \"{}\" already exists.".format(
                    self._data["name"]
                )

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

        if key not in self.columns:
            return False

        if role == QtCore.Qt.EditRole:
            self._data[key] = value

            # must return true if successful
            return True

        return False

    @property
    def id(self):
        return self._id

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
    columns = [
        "name",
        "type",
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight"
    ]
    query_projection = {
        "_id": 1,
        "name": 1,
        "type": 1,
        "data.frameStart": 1,
        "data.frameEnd": 1,
        "data.fps": 1,
        "data.resolutionWidth": 1,
        "data.resolutionHeight": 1
    }

    def __init__(self, project_doc):
        data = self.data_from_doc(project_doc)
        super(ProjectItem, self).__init__(data)

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
    columns = [
        "name",
        "type",
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight"
    ]
    editable_columns = {
        "name",
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight"
    }
    query_projection = {
        "_id": 1,
        "data.tasks": 1,
        "data.visualParent": 1,

        "name": 1,
        "type": 1,
        "data.frameStart": 1,
        "data.frameEnd": 1,
        "data.fps": 1,
        "data.resolutionWidth": 1,
        "data.resolutionHeight": 1
    }

    def __init__(self, asset_doc):
        data = self.data_from_doc(asset_doc)
        super(AssetItem, self).__init__(data)

    @classmethod
    def data_from_doc(cls, asset_doc):
        data = {
            "name": asset_doc["name"],
            "type": asset_doc["type"]
        }
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


class TaskItem(BaseItem):
    columns = [
        "name",
        "type"
    ]
    editable_columns = {
        "name",
        "type"
    }

    @classmethod
    def name_icon(cls):
        if cls._name_icon is None:
            cls._name_icon = qtawesome.icon("fa.file-o", color="#333333")
        return cls._name_icon

    def add_child(self, item, row=None):
        raise AssertionError("BUG: Can't add children to Task")
