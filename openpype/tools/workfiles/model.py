import os
import logging

from Qt import QtCore, QtGui

from avalon import style
from avalon.vendor import qtawesome
from avalon.tools.models import TreeModel, Item

log = logging.getLogger(__name__)

TASK_NAME_ROLE = QtCore.Qt.UserRole + 1
TASK_TYPE_ROLE = QtCore.Qt.UserRole + 2
TASK_ORDER_ROLE = QtCore.Qt.UserRole + 3


class FilesModel(TreeModel):
    """Model listing files with specified extensions in a root folder"""
    Columns = ["filename", "date"]

    FileNameRole = QtCore.Qt.UserRole + 2
    DateModifiedRole = QtCore.Qt.UserRole + 3
    FilePathRole = QtCore.Qt.UserRole + 4
    IsEnabled = QtCore.Qt.UserRole + 5

    def __init__(self, file_extensions, parent=None):
        super(FilesModel, self).__init__(parent=parent)

        self._root = None
        self._file_extensions = file_extensions
        self._icons = {
            "file": qtawesome.icon("fa.file-o", color=style.colors.default)
        }

    def set_root(self, root):
        self._root = root
        self.refresh()

    def _add_empty(self):
        item = Item()
        item.update({
            # Put a display message in 'filename'
            "filename": "No files found.",
            # Not-selectable
            "enabled": False,
            "date": None,
            "filepath": None
        })

        self.add_child(item)

    def refresh(self):
        self.clear()
        self.beginResetModel()

        root = self._root

        if not root:
            self.endResetModel()
            return

        if not os.path.exists(root):
            # Add Work Area does not exist placeholder
            log.debug("Work Area does not exist: %s", root)
            message = "Work Area does not exist. Use Save As to create it."
            item = Item({
                "filename": message,
                "date": None,
                "filepath": None,
                "enabled": False,
                "icon": qtawesome.icon("fa.times", color=style.colors.mid)
            })
            self.add_child(item)
            self.endResetModel()
            return

        extensions = self._file_extensions

        for filename in os.listdir(root):
            path = os.path.join(root, filename)
            if os.path.isdir(path):
                continue

            ext = os.path.splitext(filename)[1]
            if extensions and ext not in extensions:
                continue

            modified = os.path.getmtime(path)

            item = Item({
                "filename": filename,
                "date": modified,
                "filepath": path
            })

            self.add_child(item)

        if self.rowCount() == 0:
            self._add_empty()

        self.endResetModel()

    def has_filenames(self):
        for item in self._root_item.children():
            if item.get("enabled", True):
                return True
        return False

    def rowCount(self, parent=None):
        if parent is None or not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.childCount()

    def data(self, index, role):
        if not index.isValid():
            return

        if role == QtCore.Qt.DecorationRole:
            # Add icon to filename column
            item = index.internalPointer()
            if index.column() == 0:
                if item["filepath"]:
                    return self._icons["file"]
                return item.get("icon", None)

        if role == self.FileNameRole:
            item = index.internalPointer()
            return item["filename"]

        if role == self.DateModifiedRole:
            item = index.internalPointer()
            return item["date"]

        if role == self.FilePathRole:
            item = index.internalPointer()
            return item["filepath"]

        if role == self.IsEnabled:
            item = index.internalPointer()
            return item.get("enabled", True)

        return super(FilesModel, self).data(index, role)

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

        return super(FilesModel, self).headerData(section, orientation, role)


class TasksProxyModel(QtCore.QSortFilterProxyModel):
    def lessThan(self, x_index, y_index):
        x_order = x_index.data(TASK_ORDER_ROLE)
        y_order = y_index.data(TASK_ORDER_ROLE)
        if x_order is not None and y_order is not None:
            if x_order < y_order:
                return True
            if x_order > y_order:
                return False

        elif x_order is None and y_order is not None:
            return True

        elif y_order is None and x_order is not None:
            return False

        x_name = x_index.data(QtCore.Qt.DisplayRole)
        y_name = y_index.data(QtCore.Qt.DisplayRole)
        if x_name == y_name:
            return True

        if x_name == tuple(sorted((x_name, y_name)))[0]:
            return False
        return True


class TasksModel(QtGui.QStandardItemModel):
    """A model listing the tasks combined for a list of assets"""
    def __init__(self, dbcon, parent=None):
        super(TasksModel, self).__init__(parent=parent)
        self.dbcon = dbcon
        self._default_icon = qtawesome.icon(
            "fa.male",
            color=style.colors.default
        )
        self._no_tasks_icon = qtawesome.icon(
            "fa.exclamation-circle",
            color=style.colors.mid
        )
        self._cached_icons = {}
        self._project_task_types = {}

        self._refresh_task_types()

    def _refresh_task_types(self):
        # Get the project configured icons from database
        project = self.dbcon.find_one(
            {"type": "project"},
            {"config.tasks"}
        )
        tasks = project["config"].get("tasks") or {}
        self._project_task_types = tasks

    def _try_get_awesome_icon(self, icon_name):
        icon = None
        if icon_name:
            try:
                icon = qtawesome.icon(
                    "fa.{}".format(icon_name),
                    color=style.colors.default
                )

            except Exception:
                pass
        return icon

    def headerData(self, section, orientation, role):
        # Show nice labels in the header
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
        ):
            if section == 0:
                return "Tasks"

        return super(TasksModel, self).headerData(section, orientation, role)

    def _get_icon(self, task_icon, task_type_icon):
        if task_icon in self._cached_icons:
            return self._cached_icons[task_icon]

        icon = self._try_get_awesome_icon(task_icon)
        if icon is not None:
            self._cached_icons[task_icon] = icon
            return icon

        if task_type_icon in self._cached_icons:
            icon = self._cached_icons[task_type_icon]
            self._cached_icons[task_icon] = icon
            return icon

        icon = self._try_get_awesome_icon(task_type_icon)
        if icon is None:
            icon = self._default_icon

        self._cached_icons[task_icon] = icon
        self._cached_icons[task_type_icon] = icon

        return icon

    def set_asset(self, asset_doc):
        """Set assets to track by their database id

        Arguments:
            asset_doc (dict): Asset document from MongoDB.
        """
        self.clear()

        if not asset_doc:
            return

        asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
        items = []
        for task_name, task_info in asset_tasks.items():
            task_icon = task_info.get("icon")
            task_type = task_info.get("type")
            task_order = task_info.get("order")
            task_type_info = self._project_task_types.get(task_type) or {}
            task_type_icon = task_type_info.get("icon")
            icon = self._get_icon(task_icon, task_type_icon)

            label = "{} ({})".format(task_name, task_type or "type N/A")
            item = QtGui.QStandardItem(label)
            item.setData(task_name, TASK_NAME_ROLE)
            item.setData(task_type, TASK_TYPE_ROLE)
            item.setData(task_order, TASK_ORDER_ROLE)
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            items.append(item)

        if not items:
            item = QtGui.QStandardItem("No task")
            item.setData(self._no_tasks_icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            items.append(item)

        self.invisibleRootItem().appendRows(items)
