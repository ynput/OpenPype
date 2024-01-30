import qtawesome
from qtpy import QtWidgets, QtCore, QtGui

from openpype.style import (
    get_default_entity_icon_color,
    get_disabled_entity_icon_color,
)
from openpype.tools.utils import TreeView
from openpype.tools.utils.delegates import PrettyTimeDelegate

FILENAME_ROLE = QtCore.Qt.UserRole + 1
FILEPATH_ROLE = QtCore.Qt.UserRole + 2
DATE_MODIFIED_ROLE = QtCore.Qt.UserRole + 3


class WorkAreaFilesModel(QtGui.QStandardItemModel):
    """A model for workare workfiles.

    Args:
        controller (AbstractWorkfilesFrontend): The control object.
    """

    def __init__(self, controller):
        super(WorkAreaFilesModel, self).__init__()

        self.setColumnCount(2)

        self.setHeaderData(0, QtCore.Qt.Horizontal, "Name")
        self.setHeaderData(1, QtCore.Qt.Horizontal, "Date Modified")

        controller.register_event_callback(
            "selection.folder.changed",
            self._on_folder_changed
        )
        controller.register_event_callback(
            "selection.task.changed",
            self._on_task_changed
        )
        controller.register_event_callback(
            "workfile_duplicate.finished",
            self._on_duplicate_finished
        )
        controller.register_event_callback(
            "save_as.finished",
            self._on_save_as_finished
        )

        self._file_icon = qtawesome.icon(
            "fa.file-o",
            color=get_default_entity_icon_color()
        )
        self._controller = controller
        self._items_by_filename = {}
        self._missing_context_item = None
        self._missing_context_used = False
        self._empty_root_item = None
        self._empty_item_used = False
        self._published_mode = False
        self._selected_folder_id = None
        self._selected_task_id = None

        self._add_missing_context_item()

    def get_index_by_filename(self, filename):
        item = self._items_by_filename.get(filename)
        if item is None:
            return QtCore.QModelIndex()
        return self.indexFromItem(item)

    def refresh(self):
        if not self._published_mode:
            self._fill_items()

    def _get_missing_context_item(self):
        if self._missing_context_item is None:
            message = "Select folder and task"
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

    def _clear_items(self):
        self._remove_missing_context_item()
        self._remove_empty_item()
        if self._items_by_filename:
            root = self.invisibleRootItem()
            root.removeRows(0, root.rowCount())
            self._items_by_filename = {}

    def _add_missing_context_item(self):
        if self._missing_context_used:
            return
        self._clear_items()
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
            message = "Work Area is empty.."
            item = QtGui.QStandardItem(message)
            icon = qtawesome.icon(
                "fa.exclamation-circle",
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
        self._clear_items()
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
        self._selected_folder_id = event["folder_id"]
        if not self._published_mode:
            self._fill_items()

    def _on_task_changed(self, event):
        self._selected_folder_id = event["folder_id"]
        self._selected_task_id = event["task_id"]
        if not self._published_mode:
            self._fill_items()

    def _on_duplicate_finished(self, event):
        if event["failed"]:
            return

        if not self._published_mode:
            self._fill_items()

    def _on_save_as_finished(self, event):
        if event["failed"]:
            return

        if not self._published_mode:
            self._fill_items()

    def _fill_items(self):
        folder_id = self._selected_folder_id
        task_id = self._selected_task_id
        if not folder_id or not task_id:
            self._add_missing_context_item()
            return

        file_items = self._controller.get_workarea_file_items(
            folder_id, task_id
        )
        root_item = self.invisibleRootItem()
        if not file_items:
            self._add_empty_item()
            return
        self._remove_empty_item()
        self._remove_missing_context_item()

        items_to_remove = set(self._items_by_filename.keys())
        new_items = []
        for file_item in file_items:
            filename = file_item.filename
            if filename in self._items_by_filename:
                items_to_remove.discard(filename)
                item = self._items_by_filename[filename]
            else:
                item = QtGui.QStandardItem()
                new_items.append(item)
                item.setColumnCount(self.columnCount())
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                )
                item.setData(self._file_icon, QtCore.Qt.DecorationRole)
                item.setData(file_item.filename, QtCore.Qt.DisplayRole)
                item.setData(file_item.filename, FILENAME_ROLE)

            item.setData(file_item.filepath, FILEPATH_ROLE)
            item.setData(file_item.modified, DATE_MODIFIED_ROLE)

            self._items_by_filename[file_item.filename] = item

        if new_items:
            root_item.appendRows(new_items)

        for filename in items_to_remove:
            item = self._items_by_filename.pop(filename)
            root_item.removeRow(item.row())

        if root_item.rowCount() == 0:
            self._add_empty_item()

    def flags(self, index):
        # Use flags of first column for all columns
        if index.column() != 0:
            index = self.index(index.row(), 0, index.parent())
        return super(WorkAreaFilesModel, self).flags(index)

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

        return super(WorkAreaFilesModel, self).data(index, role)

    def set_published_mode(self, published_mode):
        if self._published_mode == published_mode:
            return
        self._published_mode = published_mode
        if not published_mode:
            self._fill_items()


class WorkAreaFilesWidget(QtWidgets.QWidget):
    """Workarea files widget.

    Args:
        controller (AbstractWorkfilesFrontend): The control object.
        parent (QtWidgets.QWidget): The parent widget.
    """

    selection_changed = QtCore.Signal()
    open_current_requested = QtCore.Signal()
    duplicate_requested = QtCore.Signal()

    def __init__(self, controller, parent):
        super(WorkAreaFilesWidget, self).__init__(parent)

        view = TreeView(self)
        view.setSortingEnabled(True)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # Smaller indentation
        view.setIndentation(0)

        model = WorkAreaFilesModel(controller)
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
        view.double_clicked.connect(self._on_mouse_double_click)
        view.customContextMenuRequested.connect(self._on_context_menu)

        controller.register_event_callback(
            "expected_selection_changed",
            self._on_expected_selection_change
        )

        self._view = view
        self._model = model
        self._proxy_model = proxy_model
        self._time_delegate = time_delegate
        self._controller = controller

        self._published_mode = False

    def set_published_mode(self, published_mode):
        """Set the published mode.

        Widget should ignore most of events when in published mode is enabled.

        Args:
            published_mode (bool): The published mode.
        """

        self._model.set_published_mode(published_mode)
        self._published_mode = published_mode

    def set_text_filter(self, text_filter):
        """Set the text filter.

        Args:
            text_filter (str): The text filter.
        """

        self._proxy_model.setFilterFixedString(text_filter)

    def _get_selected_info(self):
        selection_model = self._view.selectionModel()
        filepath = None
        filename = None
        for index in selection_model.selectedIndexes():
            filepath = index.data(FILEPATH_ROLE)
            filename = index.data(FILENAME_ROLE)
        return {
            "filepath": filepath,
            "filename": filename,
        }

    def get_selected_path(self):
        """Selected filepath.

        Returns:
            Union[str, None]: The selected filepath or None if nothing is
                selected.
        """
        return self._get_selected_info()["filepath"]

    def _on_selection_change(self):
        filepath = self.get_selected_path()
        self._controller.set_selected_workfile_path(filepath)

    def _on_mouse_double_click(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.open_current_requested.emit()

    def _on_context_menu(self, point):
        index = self._view.indexAt(point)
        if not index.isValid():
            return

        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return

        menu = QtWidgets.QMenu(self)

        # Duplicate
        action = QtWidgets.QAction("Duplicate", menu)
        tip = "Duplicate selected file."
        action.setToolTip(tip)
        action.setStatusTip(tip)
        action.triggered.connect(self._on_duplicate_pressed)
        menu.addAction(action)

        # Show the context action menu
        global_point = self._view.mapToGlobal(point)
        _ = menu.exec_(global_point)

    def _on_duplicate_pressed(self):
        self.duplicate_requested.emit()

    def _on_expected_selection_change(self, event):
        workfile_info = event["workfile"]
        if not workfile_info["current"]:
            return

        self._model.refresh()

        workfile_name = workfile_info["name"]
        if (
            workfile_name is not None
            and workfile_name != self._get_selected_info()["filename"]
        ):
            index = self._model.get_index_by_filename(workfile_name)
            if index.isValid():
                proxy_index = self._proxy_model.mapFromSource(index)
                self._view.setCurrentIndex(proxy_index)

        self._controller.expected_workfile_selected(
            event["folder"]["id"], event["task"]["name"], workfile_name
        )
