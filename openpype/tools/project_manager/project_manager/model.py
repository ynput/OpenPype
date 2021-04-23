import collections
from queue import Queue
from uuid import uuid4

from .constants import (
    IDENTIFIER_ROLE,
    COLUMNS_ROLE
)

from avalon.api import AvalonMongoDB
from avalon.vendor import qtawesome

from Qt import QtCore


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

    def __init__(self, parent=None):
        super(HierarchyModel, self).__init__(parent)
        self._root_item = None
        self._items_by_id = {}
        self.dbcon = AvalonMongoDB()

        self._hierarchy_mode = True
        self._reset_root_item()

    def change_edit_mode(self, hiearchy_mode):
        self._hierarchy_mode = hiearchy_mode

    @property
    def items_by_id(self):
        return self._items_by_id

    def _reset_root_item(self):
        self._root_item = RootItem(self)

    def set_project(self, project_doc):
        self.clear()

        item = ProjectItem(project_doc)
        self.add_item(item)

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

        data = {"name": name}
        new_child = AssetItem(data)

        return self.add_item(new_child, parent, new_row)

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

    def add_new_item(self, parent):
        data = {"name": "Test {}".format(parent.rowCount())}
        new_child = AssetItem(data)

        return self.add_item(new_child, parent)

    def add_item(self, item, parent=None, row=None):
        if parent is None:
            parent = self._root_item

        if row is None:
            row = parent.rowCount()

        parent_index = self.index_from_item(parent.row(), 0, parent.parent())
        self.beginInsertRows(parent_index, row, row)

        if item.parent() is not parent:
            item.set_parent(parent)

        parent.add_child(item, row)

        if item.id not in self._items_by_id:
            self._items_by_id[item.id] = item

        self.endInsertRows()

        self.rowsInserted.emit(parent_index, row, row)

        return self.index_from_item(row, 0, parent)

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

                    children.pop(child_id)
                    child_item.set_parent(None)
                    self._items_by_id.pop(child_id)

        self.endRemoveRows()

    def move_vertical(self, index, direction):
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
            if src_parent.rowCount() == 1:
                return

            if item.row() == 0:
                parent_row = item.row() + 1
            else:
                parent_row = item.row() - 1
            dst_parent = src_parent.child(parent_row)
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

    def move_horizontal(self, index, direction):
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
    columns = ["name"]
    _name_icon = None

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

        if role == COLUMNS_ROLE:
            return self.columns

        if key not in self.columns:
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
        if key in self.columns:
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
    def __init__(self, data=None):
        super(ProjectItem, self).__init__(data)
        self._data["name"] = "project"

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
    @classmethod
    def name_icon(cls):
        if cls._name_icon is None:
            cls._name_icon = qtawesome.icon("fa.file-o", color="#333333")
        return cls._name_icon
