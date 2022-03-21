import os
import logging

from Qt import QtCore, QtGui
import qtawesome

from openpype.style import (
    get_default_entity_icon_color,
    get_disabled_entity_icon_color,
)


log = logging.getLogger(__name__)

FILEPATH_ROLE = QtCore.Qt.UserRole + 2
DATE_MODIFIED_ROLE = QtCore.Qt.UserRole + 3
ITEM_ID_ROLE = QtCore.Qt.UserRole + 4


class WorkAreaFilesModel(QtGui.QStandardItemModel):
    def __init__(self, extensions, *args, **kwargs):
        super(WorkAreaFilesModel, self).__init__(*args, **kwargs)

        self.setColumnCount(2)

        self._root = None
        self._file_extensions = extensions
        self._invalid_path_item = None
        self._empty_root_item = None
        self._file_icon = qtawesome.icon(
            "fa.file-o",
            color=get_default_entity_icon_color()
        )
        self._invalid_item_visible = False
        self._items_by_filename = {}

    def _get_invalid_path_item(self):
        if self._invalid_path_item is None:
            message = "Work Area does not exist. Use Save As to create it."
            item = QtGui.QStandardItem(message)
            icon = qtawesome.icon(
                "fa.times",
                color=get_disabled_entity_icon_color()
            )
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            item.setColumnCount(self.columnCount())
            self._invalid_path_item = item
        return self._invalid_path_item

    def _get_empty_root_item(self):
        if self._empty_root_item is None:
            message = "Work Area does not exist. Use Save As to create it."
            item = QtGui.QStandardItem(message)
            icon = qtawesome.icon(
                "fa.times",
                color=get_disabled_entity_icon_color()
            )
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            item.setColumnCount(self.columnCount())
            self._empty_root_item = item
        return self._empty_root_item

    def set_root(self, root):
        self._root = root
        if root and not os.path.exists(root):
            log.debug("Work Area does not exist: {}".format(root))
        self.refresh()

    def _clear(self):
        root_item = self.invisibleRootItem()
        rows = root_item.rowCount()
        if rows > 0:
            if self._invalid_item_visible:
                for row in range(rows):
                    root_item.takeRow(row)
            else:
                root_item.removeRows(0, rows)
        self._items_by_filename = {}

    def refresh(self):
        root_item = self.invisibleRootItem()
        if not self._root or not os.path.exists(self._root):
            self._clear()
            # Add Work Area does not exist placeholder
            item = self._get_invalid_path_item()
            root_item.appendRow(item)
            self._invalid_item_visible = True
            return

        if self._invalid_item_visible:
            self._clear()

        new_items = []
        items_to_remove = set(self._items_by_filename.keys())
        for filename in os.listdir(self._root):
            filepath = os.path.join(self._root, filename)
            if os.path.isdir(filepath):
                continue

            ext = os.path.splitext(filename)[1]
            if ext not in self._file_extensions:
                continue

            modified = os.path.getmtime(filepath)

            if filename in items_to_remove:
                items_to_remove.remove(filename)
                item = self._items_by_filename[filename]
            else:
                item = QtGui.QStandardItem(filename)
                item.setColumnCount(self.columnCount())
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                )
                item.setData(self._file_icon, QtCore.Qt.DecorationRole)
                new_items.append(item)
                self._items_by_filename[filename] = item
            item.setData(filepath, FILEPATH_ROLE)
            item.setData(modified, DATE_MODIFIED_ROLE)

        if new_items:
            root_item.appendRows(new_items)

        for filename in items_to_remove:
            item = self._items_by_filename.pop(filename)
            root_item.removeRow(item.row())

        if root_item.rowCount() > 0:
            self._invalid_item_visible = False
        else:
            self._invalid_item_visible = True
            item = self._get_empty_root_item()
            root_item.appendRow(item)

    def has_valid_items(self):
        return not self._invalid_item_visible

    def flags(self, index):
        if index.column() != 0:
            index = self.index(index.row(), 0, index.parent())
        return super(WorkAreaFilesModel, self).flags(index)

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        if index.column() == 1:
            if role == QtCore.Qt.DecorationRole:
                return None

            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                role = DATE_MODIFIED_ROLE
            index = self.index(index.row(), 0, index.parent())

        return super(WorkAreaFilesModel, self).data(index, role)

    def headerData(self, section, orientation, role):
        # Show nice labels in the header
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
        ):
            if section == 0:
                return "Name"
            elif section == 1:
                return "Date modified"

        return super(WorkAreaFilesModel, self).headerData(
            section, orientation, role
        )
