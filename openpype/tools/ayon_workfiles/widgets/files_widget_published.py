import qtawesome
from qtpy import QtWidgets, QtCore, QtGui

from openpype.style import (
    get_default_entity_icon_color,
    get_disabled_entity_icon_color,
)
from openpype.tools.utils.delegates import PrettyTimeDelegate
from .utils import TreeView


REPRE_ID_ROLE = QtCore.Qt.UserRole + 1
FILEPATH_ROLE = QtCore.Qt.UserRole + 2
DATE_MODIFIED_ROLE = QtCore.Qt.UserRole + 3


class PublishedFilesModel(QtGui.QStandardItemModel):
    """A model for displaying files.

    Args:
        controller (AbstractControl): The control object.
    """

    def __init__(self, controller):
        super(PublishedFilesModel, self).__init__()

        self.setColumnCount(2)

        controller.register_event_callback(
            "selection.task.changed",
            self._on_task_changed
        )
        controller.register_event_callback(
            "selection.folder.changed",
            self._on_folder_changed
        )

        self._file_icon = qtawesome.icon(
            "fa.file-o",
            color=get_default_entity_icon_color()
        )
        self._controller = controller
        self._items_by_id = {}
        self._missing_context_item = None
        self._missing_context_used = False
        self._empty_root_item = None
        self._empty_item_used = False

        self._published_mode = False
        self._context_select_mode = False

        self._last_folder_id = None
        self._last_task_id = None

        self._selected_folder_id = None
        self._selected_task_id = None

        self._add_empty_item()

    def clear(self):
        self._items_by_id = {}
        self._remove_missing_context_item()
        self._remove_empty_item()
        super(PublishedFilesModel, self).clear()

    def set_published_mode(self, published_mode):
        if self._published_mode == published_mode:
            return
        self._published_mode = published_mode
        if published_mode:
            self._fill_items()

    def _get_missing_context_item(self):
        if self._missing_context_item is None:
            message = "Select folder"
            item = QtGui.QStandardItem(message)
            icon = qtawesome.icon(
                "fa.times",
                color=get_disabled_entity_icon_color()
            )
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            item.setColumnCount(self.columnCount())
            self._missing_context_item = item
        return self._missing_context_item

    def _add_missing_context_item(self):
        if self._missing_context_used:
            return
        self.clear()
        root_item = self.invisibleRootItem()
        root_item.appendRow(self._get_missing_context_item())
        self._missing_context_used = True

    def _remove_missing_context_item(self):
        if not self._missing_context_used:
            return
        root_item = self.invisibleRootItem()
        root_item.takeRow(self._missing_context_item.row())
        self._missing_context_used = False

    def _get_empty_root_item(self):
        if self._empty_root_item is None:
            message = "Didn't find any published workfiles."
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

    def _add_empty_item(self):
        if self._empty_item_used:
            return
        self.clear()
        root_item = self.invisibleRootItem()
        root_item.appendRow(self._get_empty_root_item())
        self._empty_item_used = True

    def _remove_empty_item(self):
        if not self._empty_item_used:
            return
        root_item = self.invisibleRootItem()
        root_item.takeRow(self._empty_root_item.row())
        self._empty_item_used = False

    def _on_folder_changed(self, event):
        if self._context_select_mode:
            self._selected_folder_id = event["folder_id"]
            self._selected_task_id = None
            return

        self._last_folder_id = event["folder_id"]
        self._last_task_id = None
        if self._published_mode:
            self._fill_items()

    def _on_task_changed(self, event):
        if self._context_select_mode:
            self._selected_folder_id = event["folder_id"]
            self._selected_task_id = event["task_id"]
            return

        self._last_folder_id = event["folder_id"]
        self._last_task_id = event["task_id"]
        if self._published_mode:
            self._fill_items()

    def _fill_items(self):
        folder_id = self._last_folder_id
        task_id = self._last_task_id
        if not folder_id:
            self._add_missing_context_item()
            return

        file_items = self._controller.get_published_file_items(
            folder_id, task_id
        )
        root_item = self.invisibleRootItem()
        if not file_items:
            self._add_empty_item()
            return
        self._remove_empty_item()
        self._remove_missing_context_item()

        items_to_remove = set(self._items_by_id.keys())
        new_items = []
        for file_item in file_items:
            repre_id = file_item.filename
            if repre_id in self._items_by_id:
                items_to_remove.discard(repre_id)
                item = self._items_by_id[repre_id]
            else:
                item = QtGui.QStandardItem()
                new_items.append(item)
                item.setColumnCount(self.columnCount())
                item.setData(self._file_icon, QtCore.Qt.DecorationRole)
                item.setData(file_item.filename, QtCore.Qt.DisplayRole)
                item.setData(file_item.representation_id, REPRE_ID_ROLE)

            if file_item.exists:
                flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            else:
                flags = QtCore.Qt.NoItemFlags

            item.setFlags(flags)
            item.setData(file_item.filepath, FILEPATH_ROLE)
            item.setData(file_item.modified, DATE_MODIFIED_ROLE)

            self._items_by_id[file_item.filename] = item

        if new_items:
            root_item.appendRows(new_items)

        for repre_id in items_to_remove:
            item = self._items_by_id.pop(repre_id)
            root_item.removeRow(item.row())

        if root_item.rowCount() == 0:
            self._add_empty_item()

    def flags(self, index):
        # Use flags of first column for all columns
        if index.column() != 0:
            index = self.index(index.row(), 0, index.parent())
        return super(PublishedFilesModel, self).flags(index)

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

        return super(PublishedFilesModel, self).headerData(
            section, orientation, role
        )

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        # Handle roles for first column
        if index.column() == 1:
            if role == QtCore.Qt.DecorationRole:
                return None

            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                role = DATE_MODIFIED_ROLE
            index = self.index(index.row(), 0, index.parent())

        return super(PublishedFilesModel, self).data(index, role)


class PublishedFilesWidget(QtWidgets.QWidget):
    selection_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(PublishedFilesWidget, self).__init__(parent)

        view = TreeView(self)
        view.setSortingEnabled(True)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # Smaller indentation
        view.setIndentation(3)

        model = PublishedFilesModel(controller)
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(model)
        proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy_model.setDynamicSortFilter(True)

        view.setModel(proxy_model)

        time_delegate = PrettyTimeDelegate()
        view.setItemDelegateForColumn(1, time_delegate)

        # Default to a wider first filename column it is what we mostly care
        # about and the date modified is relatively small anyway.
        view.setColumnWidth(0, 330)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(view, 1)

        selection_model = view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)
        view.double_clicked_left.connect(self._on_left_double_click)

        self._view = view
        self._model = model
        self._proxy_model = proxy_model
        self._time_delegate = time_delegate
        self._controller = controller

        self._published_mode = False

    def set_published_mode(self, published_mode):
        self._model.set_published_mode(published_mode)
        self._published_mode = published_mode

    def set_text_filter(self, text_filter):
        self._proxy_model.setFilterFixedString(text_filter)

    def get_selected_repre_id(self):
        selection_model = self._view.selectionModel()
        for index in selection_model.selectedIndexes():
            repre_id = index.data(REPRE_ID_ROLE)
            if repre_id is not None:
                return repre_id
        return None

    def _on_selection_change(self):
        repre_id = self.get_selected_repre_id()
        self._controller.set_selected_representation_id(repre_id)

    def _on_left_double_click(self):
        # TODO Request save as dialog
        pass
