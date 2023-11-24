import os

import qtpy
from qtpy import QtWidgets, QtCore

from .save_as_dialog import SaveAsDialog
from .files_widget_workarea import WorkAreaFilesWidget
from .files_widget_published import PublishedFilesWidget


class FilesWidget(QtWidgets.QWidget):
    """A widget displaying files that allows to save and open files.

    Args:
        controller (AbstractWorkfilesFrontend): The control object.
        parent (QtWidgets.QWidget): The parent widget.
    """

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

        published_btns_widget = QtWidgets.QWidget(btns_widget)
        published_btn_copy_n_open = QtWidgets.QPushButton(
            "Copy && Open", published_btns_widget
        )
        published_btn_change_context = QtWidgets.QPushButton(
            "Choose different context", published_btns_widget
        )
        published_btn_cancel = QtWidgets.QPushButton(
            "Cancel", published_btns_widget
        )

        published_btns_layout = QtWidgets.QHBoxLayout(published_btns_widget)
        published_btns_layout.setContentsMargins(0, 0, 0, 0)
        published_btns_layout.addWidget(published_btn_copy_n_open, 1)
        published_btns_layout.addWidget(published_btn_change_context, 1)
        published_btns_layout.addWidget(published_btn_cancel, 1)

        btns_layout = QtWidgets.QVBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addWidget(workarea_btns_widget, 1)
        btns_layout.addWidget(published_btns_widget, 1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(files_widget, 1)
        main_layout.addWidget(btns_widget, 0)

        controller.register_event_callback(
            "selection.workarea.changed",
            self._on_workarea_path_changed
        )
        controller.register_event_callback(
            "selection.representation.changed",
            self._on_published_repre_changed
        )
        controller.register_event_callback(
            "selection.task.changed",
            self._on_task_changed
        )
        controller.register_event_callback(
            "copy_representation.finished",
            self._on_copy_representation_finished,
        )
        controller.register_event_callback(
            "workfile_save_enable.changed",
            self._on_workfile_save_enabled_change,
        )

        workarea_widget.open_current_requested.connect(
            self._on_current_open_requests)
        workarea_widget.duplicate_requested.connect(
            self._on_duplicate_request)
        workarea_btn_open.clicked.connect(self._on_workarea_open_clicked)
        workarea_btn_browse.clicked.connect(self._on_workarea_browse_clicked)
        workarea_btn_save.clicked.connect(self._on_workarea_save_clicked)

        published_widget.save_as_requested.connect(self._on_save_as_request)
        published_btn_copy_n_open.clicked.connect(
            self._on_published_save_clicked)
        published_btn_change_context.clicked.connect(
            self._on_published_change_context_clicked)
        published_btn_cancel.clicked.connect(
            self._on_published_cancel_clicked)

        self._selected_folder_id = None
        self._selected_task_id = None
        self._selected_task_name = None

        self._pre_select_folder_id = None
        self._pre_select_task_name = None

        self._select_context_mode = False
        self._valid_selected_context = False
        self._valid_representation_id = False
        self._tmp_text_filter = None
        self._is_save_enabled = True

        self._controller = controller
        self._files_widget = files_widget
        self._workarea_widget = workarea_widget
        self._published_widget = published_widget
        self._workarea_btns_widget = workarea_btns_widget
        self._published_btns_widget = published_btns_widget

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
        published_btn_cancel.setVisible(False)

    def set_published_mode(self, published_mode):
        # Make sure context selection is disabled
        self._set_select_contex_mode(False)
        # Change current widget
        self._files_widget.setCurrentWidget((
            self._published_widget
            if published_mode
            else self._workarea_widget
        ))
        # Pass the mode to the widgets, so they can start/stop handle events
        self._workarea_widget.set_published_mode(published_mode)
        self._published_widget.set_published_mode(published_mode)

        # Change available buttons
        self._workarea_btns_widget.setVisible(not published_mode)
        self._published_btns_widget.setVisible(published_mode)

    def set_text_filter(self, text_filter):
        if self._select_context_mode:
            self._tmp_text_filter = text_filter
            return
        self._workarea_widget.set_text_filter(text_filter)
        self._published_widget.set_text_filter(text_filter)

    def _exec_save_as_dialog(self):
        """Show SaveAs dialog using currently selected context.

        Returns:
            Union[dict[str, Any], None]: Result of the dialog.
        """

        dialog = SaveAsDialog(self._controller, self)
        dialog.update_context()
        dialog.exec_()
        return dialog.get_result()

    # -------------------------------------------------------------
    # Workarea workfiles
    # -------------------------------------------------------------
    def _open_workfile(self, folder_id, task_name, filepath):
        if self._controller.has_unsaved_changes():
            result = self._save_changes_prompt()
            if result is None:
                return

            if result:
                self._controller.save_current_workfile()
        self._controller.open_workfile(folder_id, task_name, filepath)

    def _on_workarea_open_clicked(self):
        path = self._workarea_widget.get_selected_path()
        if not path:
            return
        folder_id = self._selected_folder_id
        task_id = self._selected_task_id
        self._open_workfile(folder_id, task_id, path)

    def _on_current_open_requests(self):
        self._on_workarea_open_clicked()

    def _on_duplicate_request(self):
        filepath = self._workarea_widget.get_selected_path()
        if filepath is None:
            return

        result = self._exec_save_as_dialog()
        if result is None:
            return
        self._controller.duplicate_workfile(
            filepath,
            result["workdir"],
            result["filename"]
        )

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
        if not filepath:
            return

        folder_id = self._selected_folder_id
        task_id = self._selected_task_id
        self._open_workfile(folder_id, task_id, filepath)

    def _on_workarea_save_clicked(self):
        result = self._exec_save_as_dialog()
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

    # -------------------------------------------------------------
    # Published workfiles
    # -------------------------------------------------------------
    def _update_published_btns_state(self):
        enabled = (
            self._valid_representation_id
            and self._valid_selected_context
            and self._is_save_enabled
        )
        self._published_btn_copy_n_open.setEnabled(enabled)
        self._published_btn_change_context.setEnabled(enabled)

    def _update_workarea_btns_state(self):
        enabled = self._is_save_enabled
        self._workarea_btn_save.setEnabled(enabled)

    def _on_published_repre_changed(self, event):
        self._valid_representation_id = event["representation_id"] is not None
        self._update_published_btns_state()

    def _on_task_changed(self, event):
        self._selected_folder_id = event["folder_id"]
        self._selected_task_id = event["task_id"]
        self._selected_task_name = event["task_name"]
        self._valid_selected_context = (
            self._selected_folder_id is not None
            and self._selected_task_id is not None
        )
        self._update_published_btns_state()

    def _on_published_save_clicked(self):
        result = self._exec_save_as_dialog()
        if result is None:
            return

        repre_info = self._published_widget.get_selected_repre_info()
        self._controller.copy_workfile_representation(
            repre_info["representation_id"],
            repre_info["filepath"],
            result["folder_id"],
            result["task_id"],
            result["workdir"],
            result["filename"],
            result["template_key"],
        )

    def _on_save_as_request(self):
        self._on_published_save_clicked()

    def _set_select_contex_mode(self, enabled):
        if self._select_context_mode is enabled:
            return

        if enabled:
            self._pre_select_folder_id = self._selected_folder_id
            self._pre_select_task_name = self._selected_task_name
        else:
            self._pre_select_folder_id = None
            self._pre_select_task_name = None
        self._select_context_mode = enabled
        self._published_btn_cancel.setVisible(enabled)
        self._published_btn_change_context.setVisible(not enabled)
        self._published_widget.set_select_context_mode(enabled)

        if not enabled and self._tmp_text_filter is not None:
            self.set_text_filter(self._tmp_text_filter)
            self._tmp_text_filter = None

    def _on_published_change_context_clicked(self):
        self._set_select_contex_mode(True)

    def _should_set_pre_select_context(self):
        if self._pre_select_folder_id is None:
            return False
        if self._pre_select_folder_id != self._selected_folder_id:
            return True
        if self._pre_select_task_name is None:
            return False
        return self._pre_select_task_name != self._selected_task_name

    def _on_published_cancel_clicked(self):
        folder_id = self._pre_select_folder_id
        task_name = self._pre_select_task_name
        representation_id = self._published_widget.get_selected_repre_id()
        should_change_selection = self._should_set_pre_select_context()
        self._set_select_contex_mode(False)
        if should_change_selection:
            self._controller.set_expected_selection(
                folder_id, task_name, representation_id=representation_id
            )

    def _on_copy_representation_finished(self, event):
        """Callback for when copy representation is finished.

        Make sure that select context mode is disabled when representation
        copy is finished.

        Args:
            event (Event): Event object.
        """

        if not event["failed"]:
            self._set_select_contex_mode(False)

    def _on_workfile_save_enabled_change(self, event):
        enabled = event["enabled"]
        self._is_save_enabled = enabled
        self._update_published_btns_state()
        self._update_workarea_btns_state()

    def _save_changes_prompt(self):
        """Ask user if wants to save changes to current file.

        Returns:
            Union[bool, None]: True if user wants to save changes, False if
                user does not want to save changes, None if user cancels
                operation.
        """
        messagebox = QtWidgets.QMessageBox(parent=self)
        messagebox.setWindowFlags(
            messagebox.windowFlags() | QtCore.Qt.FramelessWindowHint
        )
        messagebox.setIcon(QtWidgets.QMessageBox.Warning)
        messagebox.setWindowTitle("Unsaved Changes!")
        messagebox.setText(
            "There are unsaved changes to the current file."
            "\nDo you want to save the changes?"
        )
        messagebox.setStandardButtons(
            QtWidgets.QMessageBox.Yes
            | QtWidgets.QMessageBox.No
            | QtWidgets.QMessageBox.Cancel
        )

        result = messagebox.exec_()
        if result == QtWidgets.QMessageBox.Yes:
            return True
        if result == QtWidgets.QMessageBox.No:
            return False
        return None
