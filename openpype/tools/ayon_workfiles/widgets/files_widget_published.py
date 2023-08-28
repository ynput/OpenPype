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
        elif self._context_select_mode:
            self.set_select_context_mode(False)

    def set_select_context_mode(self, select_mode):
        if self._context_select_mode is select_mode:
            return
        self._context_select_mode = select_mode
        if not select_mode and self._published_mode:
            self._fill_items()

    def get_index_by_representation_id(self, representation_id):
        item = self._items_by_id.get(representation_id)
        if item is None:
            return QtCore.QModelIndex()
        return self.indexFromItem(item)

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
        self._last_folder_id = event["folder_id"]
        self._last_task_id = None
        if self._context_select_mode:
            return

        if self._published_mode:
            self._fill_items()

    def _on_task_changed(self, event):
        self._last_folder_id = event["folder_id"]
        self._last_task_id = event["task_id"]
        if self._context_select_mode:
            return

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
            repre_id = file_item.representation_id
            if repre_id in self._items_by_id:
                items_to_remove.discard(repre_id)
                item = self._items_by_id[repre_id]
            else:
                item = QtGui.QStandardItem()
                new_items.append(item)
                item.setColumnCount(self.columnCount())
                item.setData(self._file_icon, QtCore.Qt.DecorationRole)
                item.setData(file_item.filename, QtCore.Qt.DisplayRole)
                item.setData(repre_id, REPRE_ID_ROLE)

            if file_item.exists:
                flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            else:
                flags = QtCore.Qt.NoItemFlags

            item.setFlags(flags)
            item.setData(file_item.filepath, FILEPATH_ROLE)
            item.setData(file_item.modified, DATE_MODIFIED_ROLE)

            self._items_by_id[repre_id] = item

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


class SelectContextOverlay(QtWidgets.QFrame):
    project_selected = QtCore.Signal(str)

    def __init__(self, parent):
        super(SelectContextOverlay, self).__init__(parent)
        self.setObjectName("OverlayFrame")

        label_widget = QtWidgets.QLabel(
            "Please choose context on the left<br/>&lt",
            self
        )
        label_widget.setAlignment(QtCore.Qt.AlignCenter)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(label_widget, 1, QtCore.Qt.AlignCenter)

        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._parent = parent

    def setVisible(self, visible):
        super(SelectContextOverlay, self).setVisible(visible)
        if visible:
            self._parent.installEventFilter(self)
            self.resize(self._parent.size())
        else:
            self._parent.removeEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Resize:
            self.resize(obj.size())

        return super(SelectContextOverlay, self).eventFilter(obj, event)


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

        select_overlay = SelectContextOverlay(view)
        select_overlay.setVisible(False)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(view, 1)

        selection_model = view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)
        view.double_clicked_left.connect(self._on_left_double_click)

        controller.register_event_callback(
            "expected_selection_changed",
            self._on_expected_selection_change
        )

        self._view = view
        self._select_overlay = select_overlay
        self._model = model
        self._proxy_model = proxy_model
        self._time_delegate = time_delegate
        self._controller = controller

    def set_published_mode(self, published_mode):
        self._model.set_published_mode(published_mode)

    def set_select_context_mode(self, select_mode):
        self._model.set_select_context_mode(select_mode)
        self._select_overlay.setVisible(select_mode)

    def set_text_filter(self, text_filter):
        self._proxy_model.setFilterFixedString(text_filter)

    def get_selected_repre_info(self):
        selection_model = self._view.selectionModel()
        representation_id = None
        filepath = None
        for index in selection_model.selectedIndexes():
            representation_id = index.data(REPRE_ID_ROLE)
            filepath = index.data(FILEPATH_ROLE)

        return {
            "representation_id": representation_id,
            "filepath": filepath,
        }

    def get_selected_repre_id(self):
        return self.get_selected_repre_info()["representation_id"]

    def _on_selection_change(self):
        repre_id = self.get_selected_repre_id()
        self._controller.set_selected_representation_id(repre_id)

    def _on_left_double_click(self):
        # TODO Request save as dialog
        pass

    def _on_expected_selection_change(self, event):
        if (
            event["representation_id_selected"]
            or not event["folder_selected"]
            or (event["task_name"] and not event["task_selected"])
        ):
            return

        representation_id = event["representation_id"]
        selected_repre_id = self.get_selected_repre_id()
        if (
            representation_id is not None
            and representation_id != selected_repre_id
        ):
            index = self._model.get_index_by_representation_id(representation_id)
            if index.isValid():
                proxy_index = self._proxy_model.mapFromSource(index)
                self._view.setCurrentIndex(proxy_index)

        self._controller.expected_representation_selected(
            event["folder_id"], event["task_name"], representation_id
        )
