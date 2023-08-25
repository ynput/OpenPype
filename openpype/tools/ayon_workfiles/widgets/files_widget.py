import os

import qtpy
from qtpy import QtWidgets

from .save_as_dialog import SaveAsDialog
from .files_widget_workarea import WorkAreaFilesWidget
from .files_widget_published import PublishedFilesWidget


class FilesWidget(QtWidgets.QWidget):
    """A widget displaying files that allows to save and open files."""

    def __init__(self, controller, parent):
        super(FilesWidget, self).__init__(parent)

        files_widget = QtWidgets.QStackedWidget(self)
        workarea_widget = WorkAreaFilesWidget(controller, files_widget)
        published_widget = PublishedFilesWidget(controller, files_widget)
        files_widget.addWidget(workarea_widget)
        files_widget.addWidget(published_widget)

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
        main_layout.addWidget(files_widget, 1)
        main_layout.addWidget(btns_widget, 0)

        controller.register_event_callback(
            "workarea.selection.changed",
            self._on_workarea_path_changed
        )
        controller.register_event_callback(
            "selection.representation.changed",
            self._on_published_repre_changed
        )

        workarea_btn_open.clicked.connect(self._on_workarea_open_clicked)
        workarea_btn_browse.clicked.connect(self._on_workarea_browse_clicked)
        workarea_btn_save.clicked.connect(self._on_workarea_save_clicked)

        self._controller = controller
        self._files_widget = files_widget
        self._workarea_widget = workarea_widget
        self._workarea_btns_widget = workarea_btns_widget
        self._publish_btns_widget = publish_btns_widget

        self._workarea_btn_open = workarea_btn_open
        self._workarea_btn_browse = workarea_btn_browse
        self._workarea_btn_save = workarea_btn_save

        self._published_widget = published_widget
        self._published_btn_copy_n_open = published_btn_copy_n_open
        self._published_btn_change_context = published_btn_change_context
        self._published_btn_cancel = published_btn_cancel

        # Initial setup
        workarea_btn_open.setEnabled(False)
        published_btn_copy_n_open.setEnabled(False)
        published_btn_change_context.setEnabled(False)
        published_btn_cancel.setEnabled(False)
        published_btn_cancel.setVisible(False)

    def set_published_mode(self, published_mode):
        self._files_widget.setCurrentWidget((
            self._published_widget
            if published_mode
            else self._workarea_widget
        ))
        self._workarea_widget.set_published_mode(published_mode)
        self._published_widget.set_published_mode(published_mode)

        self._workarea_btns_widget.setVisible(not published_mode)
        self._publish_btns_widget.setVisible(published_mode)

    def set_text_filter(self, text_filter):
        self._workarea_widget.set_text_filter(text_filter)
        self._published_widget.set_text_filter(text_filter)

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

        filepath = QtWidgets.QFileDialog.getOpenFileName(**kwargs)[0]
        if filepath:
            self._controller.open_workfile(filepath)

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

    def _on_published_repre_changed(self, event):
        valid = event["representation_id"] is not None
        self._published_btn_copy_n_open.setEnabled(valid)
        self._published_btn_change_context.setEnabled(valid)
        self._published_btn_cancel.setEnabled(valid)
        # self._published_btn_cancel.setVisible(False)
