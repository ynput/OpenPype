import os

import qtawesome
import qtpy
from qtpy import QtWidgets, QtGui, QtCore

from openpype.style import (
    get_default_entity_icon_color,
    get_disabled_entity_icon_color,
)
from openpype.tools.utils.delegates import PrettyTimeDelegate

from .save_as_dialog import SaveAsDialog

FILENAME_ROLE = QtCore.Qt.UserRole + 1
FILEPATH_ROLE = QtCore.Qt.UserRole + 2
DATE_MODIFIED_ROLE = QtCore.Qt.UserRole + 3


class WorkAreaFilesModel(QtGui.QStandardItemModel):
    """A model for displaying files.

    Args:
        control (AbstractControl): The control object.
    """

    def __init__(self, controller):
        super(WorkAreaFilesModel, self).__init__()

        self.setColumnCount(2)

        controller.register_event_callback(
            "selection.task.changed",
            self._on_task_changed
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

        self._add_empty_item()

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

    def clear(self):
        self._items_by_filename = {}
        self._remove_missing_context_item()
        self._remove_empty_item()
        super(WorkAreaFilesModel, self).clear()

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

    def _on_task_changed(self, event):
        folder_id, task_id = event["folder_id"], event["task_id"]
        if not folder_id or not task_id:
            self._add_missing_context_item()
            return

        file_items = self._controller.get_workarea_file_items(
            event["folder_id"], event["task_id"]
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
        self._published_mode = published_mode


class FilesView(QtWidgets.QTreeView):
    double_clicked_left = QtCore.Signal()
    double_clicked_right = QtCore.Signal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.double_clicked_left.emit()

        elif event.button() == QtCore.Qt.RightButton:
            self.double_clicked_right.emit()

        return super(FilesView, self).mouseDoubleClickEvent(event)


class WorkAreaFilesWidget(QtWidgets.QWidget):
    selection_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(WorkAreaFilesWidget, self).__init__(parent)

        view = FilesView(self)
        view.setSortingEnabled(True)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # Smaller indentation
        view.setIndentation(3)

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

    def get_selected_path(self):
        selection_model = self._view.selectionModel()
        for index in selection_model.selectedIndexes():
            filepath = index.data(FILEPATH_ROLE)
            if filepath is not None:
                return filepath
        return None

    def open_current_file(self):
        path = self.get_selected_path()
        if path:
            self._controller.open_workfile(path)

    def _on_selection_change(self):
        filepath = self.get_selected_path()
        self._controller.set_selected_workfile_path(filepath)

    def _on_left_double_click(self):
        self.open_current_file()


class FilesWidget(QtWidgets.QWidget):
    """A widget displaying files that allows to save and open files."""

    def __init__(self, controller, parent):
        super(FilesWidget, self).__init__(parent)

        workarea_widget = WorkAreaFilesWidget(controller, self)

        btns_widget = QtWidgets.QWidget(self)

        workarea_btns_widget = QtWidgets.QWidget(btns_widget)
        workarea_btn_open = QtWidgets.QPushButton(
            "Open", workarea_btns_widget)
        workarea_btn_browse = QtWidgets.QPushButton(
            "Browse", workarea_btns_widget)
        workarea_btn_save = QtWidgets.QPushButton(
            "Save As", workarea_btns_widget)

        workarea_btns_layout = QtWidgets.QHBoxLayout(workarea_btns_widget)
        workarea_btns_layout.setContentsMargins(0, 0, 0, 0)
        workarea_btns_layout.addWidget(workarea_btn_open, 1)
        workarea_btns_layout.addWidget(workarea_btn_browse, 1)
        workarea_btns_layout.addWidget(workarea_btn_save, 1)

        publish_btns_widget = QtWidgets.QWidget(btns_widget)
        published_btn_copy_n_open = QtWidgets.QPushButton(
            "Copy && Open", publish_btns_widget
        )
        published_btn_change_context = QtWidgets.QPushButton(
            "Choose different context", publish_btns_widget
        )
        published_btn_cancel = QtWidgets.QPushButton(
            "Cancel", publish_btns_widget
        )

        publish_btns_layout = QtWidgets.QHBoxLayout(publish_btns_widget)
        publish_btns_layout.setContentsMargins(0, 0, 0, 0)
        publish_btns_layout.addWidget(published_btn_copy_n_open, 1)
        publish_btns_layout.addWidget(published_btn_change_context, 1)
        publish_btns_layout.addWidget(published_btn_cancel, 1)

        btns_layout = QtWidgets.QVBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addWidget(workarea_btns_widget, 1)
        btns_layout.addWidget(publish_btns_widget, 1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(workarea_widget, 1)
        main_layout.addWidget(btns_widget, 0)

        controller.register_event_callback(
            "workarea.selection.changed", self._on_workarea_path_changed
        )

        workarea_btn_open.clicked.connect(self._on_workarea_open_clicked)
        workarea_btn_browse.clicked.connect(self._on_workarea_browse_clicked)
        workarea_btn_save.clicked.connect(self._on_workarea_save_clicked)

        self._controller = controller
        self._workarea_widget = workarea_widget
        self._workarea_btns_widget = workarea_btns_widget
        self._publish_btns_widget = publish_btns_widget

        self._workarea_btn_open = workarea_btn_open
        self._workarea_btn_browse = workarea_btn_browse
        self._workarea_btn_save = workarea_btn_save

        self._published_btn_copy_n_open = published_btn_copy_n_open
        self._published_btn_change_context = published_btn_change_context
        self._published_btn_cancel = published_btn_cancel

        # Initial setup
        workarea_btn_open.setEnabled(False)
        published_btn_cancel.setVisible(False)

    def set_published_mode(self, published_mode):
        self._workarea_widget.set_published_mode(published_mode)

        self._workarea_btns_widget.setVisible(not published_mode)
        self._publish_btns_widget.setVisible(published_mode)

    def set_text_filter(self, text_filter):
        self._workarea_widget.set_text_filter(text_filter)

    def _on_workarea_open_clicked(self):
        self._workarea_widget.open_current_file()

    def _on_workarea_browse_clicked(self):
        extnsions = self._controller.get_workfile_extensions()
        ext_filter = "Work File (*{0})".format(
            " *".join(extnsions)
        )
        dir_key = "directory"
        if qtpy.API in ("pyside", "pyside2", "pyside6"):
            dir_key = "dir"

        selected_context = self._controller.get_selected_context()
        workfile_root = self._controller.get_workarea_dir_by_context(
            selected_context["folder_id"], selected_context["task_id"]
        )
        # Find existing directory of workfile root
        #   - Qt will use 'cwd' instead, if path does not exist, which may lead
        #       to igniter directory
        while workfile_root:
            if os.path.exists(workfile_root):
                break
            workfile_root = os.path.dirname(workfile_root)

        kwargs = {
            "caption": "Work Files",
            "filter": ext_filter,
            dir_key: workfile_root
        }

        work_file = QtWidgets.QFileDialog.getOpenFileName(**kwargs)[0]
        if work_file:
            self._controller.open_workfile(work_file)

    def _on_workarea_save_clicked(self):
        dialog = SaveAsDialog(self._controller, self)
        dialog.update_context()
        dialog.exec_()
        result = dialog.get_result()
        if result is None:
            return
        self._controller.save_as_workfile(
            result["folder_id"],
            result["task_id"],
            result["workdir"],
            result["filename"],
            result["template_key"],
        )

    def _on_workarea_path_changed(self, event):
        valid_path = event["path"] is not None
        self._workarea_btn_open.setEnabled(valid_path)
