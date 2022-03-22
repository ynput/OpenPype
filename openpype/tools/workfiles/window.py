import os
import datetime
from Qt import QtCore, QtWidgets

from avalon import io

from openpype import style
from openpype.lib import (
    get_workfile_doc,
    create_workfile_doc,
    save_workfile_data_to_doc,
)
from openpype.tools.utils.assets_widget import SingleSelectAssetsWidget
from openpype.tools.utils.tasks_widget import TasksWidget

from .files_widget import FilesWidget
from .lib import TempPublishFiles, file_size_to_string


class SidePanelWidget(QtWidgets.QWidget):
    save_clicked = QtCore.Signal()
    published_workfile_message = (
        "<b>INFO</b>: Opened published workfiles will be stored in"
        " temp directory on your machine. Current temp size: <b>{}</b>."
    )

    def __init__(self, parent=None):
        super(SidePanelWidget, self).__init__(parent)

        details_label = QtWidgets.QLabel("Details", self)
        details_input = QtWidgets.QPlainTextEdit(self)
        details_input.setReadOnly(True)

        artist_note_widget = QtWidgets.QWidget(self)
        note_label = QtWidgets.QLabel("Artist note", artist_note_widget)
        note_input = QtWidgets.QPlainTextEdit(artist_note_widget)
        btn_note_save = QtWidgets.QPushButton("Save note", artist_note_widget)

        artist_note_layout = QtWidgets.QVBoxLayout(artist_note_widget)
        artist_note_layout.setContentsMargins(0, 0, 0, 0)
        artist_note_layout.addWidget(note_label, 0)
        artist_note_layout.addWidget(note_input, 1)
        artist_note_layout.addWidget(
            btn_note_save, 0, alignment=QtCore.Qt.AlignRight
        )

        publish_temp_widget = QtWidgets.QWidget(self)
        publish_temp_info_label = QtWidgets.QLabel(
            self.published_workfile_message.format(
                file_size_to_string(0)
            ),
            publish_temp_widget
        )
        publish_temp_info_label.setWordWrap(True)

        btn_clear_temp = QtWidgets.QPushButton(
            "Clear temp", publish_temp_widget
        )

        publish_temp_layout = QtWidgets.QVBoxLayout(publish_temp_widget)
        publish_temp_layout.setContentsMargins(0, 0, 0, 0)
        publish_temp_layout.addWidget(publish_temp_info_label, 0)
        publish_temp_layout.addWidget(
            btn_clear_temp, 0, alignment=QtCore.Qt.AlignRight
        )

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(details_label, 0)
        main_layout.addWidget(details_input, 1)
        main_layout.addWidget(artist_note_widget, 1)
        main_layout.addWidget(publish_temp_widget, 0)

        note_input.textChanged.connect(self._on_note_change)
        btn_note_save.clicked.connect(self._on_save_click)
        btn_clear_temp.clicked.connect(self._on_clear_temp_click)

        self._details_input = details_input
        self._artist_note_widget = artist_note_widget
        self._note_input = note_input
        self._btn_note_save = btn_note_save

        self._publish_temp_info_label = publish_temp_info_label
        self._publish_temp_widget = publish_temp_widget

        self._orig_note = ""
        self._workfile_doc = None

        publish_temp_widget.setVisible(False)

    def set_published_visible(self, published_visible):
        self._artist_note_widget.setVisible(not published_visible)
        self._publish_temp_widget.setVisible(published_visible)
        if published_visible:
            self.refresh_publish_temp_sizes()

    def refresh_publish_temp_sizes(self):
        temp_publish_files = TempPublishFiles()
        text = self.published_workfile_message.format(
            file_size_to_string(temp_publish_files.size)
        )
        self._publish_temp_info_label.setText(text)

    def _on_clear_temp_click(self):
        temp_publish_files = TempPublishFiles()
        temp_publish_files.clear()
        self.refresh_publish_temp_sizes()

    def _on_note_change(self):
        text = self._note_input.toPlainText()
        self._btn_note_save.setEnabled(self._orig_note != text)

    def _on_save_click(self):
        self._orig_note = self._note_input.toPlainText()
        self._on_note_change()
        self.save_clicked.emit()

    def set_context(self, asset_id, task_name, filepath, workfile_doc):
        # Check if asset, task and file are selected
        # NOTE workfile document is not requirement
        enabled = bool(asset_id) and bool(task_name) and bool(filepath)

        self._details_input.setEnabled(enabled)
        self._note_input.setEnabled(enabled)
        self._btn_note_save.setEnabled(enabled)

        # Make sure workfile doc is overridden
        self._workfile_doc = workfile_doc
        # Disable inputs and remove texts if any required arguments are missing
        if not enabled:
            self._orig_note = ""
            self._details_input.setPlainText("")
            self._note_input.setPlainText("")
            return

        orig_note = ""
        if workfile_doc:
            orig_note = workfile_doc["data"].get("note") or orig_note

        self._orig_note = orig_note
        self._note_input.setPlainText(orig_note)
        # Set as empty string
        self._details_input.setPlainText("")

        filestat = os.stat(filepath)
        size_value = file_size_to_string(filestat.st_size)

        # Append html string
        datetime_format = "%b %d %Y %H:%M:%S"
        creation_time = datetime.datetime.fromtimestamp(filestat.st_ctime)
        modification_time = datetime.datetime.fromtimestamp(filestat.st_mtime)
        lines = (
            "<b>Size:</b>",
            size_value,
            "<b>Created:</b>",
            creation_time.strftime(datetime_format),
            "<b>Modified:</b>",
            modification_time.strftime(datetime_format)
        )
        self._details_input.appendHtml("<br>".join(lines))

    def get_workfile_data(self):
        data = {
            "note": self._note_input.toPlainText()
        }
        return self._workfile_doc, data


class Window(QtWidgets.QMainWindow):
    """Work Files Window"""
    title = "Work Files"

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)
        self.setWindowTitle(self.title)
        window_flags = QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint
        if not parent:
            window_flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(window_flags)

        # Create pages widget and set it as central widget
        pages_widget = QtWidgets.QStackedWidget(self)
        self.setCentralWidget(pages_widget)

        home_page_widget = QtWidgets.QWidget(pages_widget)
        home_body_widget = QtWidgets.QWidget(home_page_widget)

        assets_widget = SingleSelectAssetsWidget(io, parent=home_body_widget)
        assets_widget.set_current_asset_btn_visibility(True)

        tasks_widget = TasksWidget(io, home_body_widget)
        files_widget = FilesWidget(home_body_widget)
        side_panel = SidePanelWidget(home_body_widget)

        pages_widget.addWidget(home_page_widget)

        # Build home
        home_page_layout = QtWidgets.QVBoxLayout(home_page_widget)
        home_page_layout.addWidget(home_body_widget)

        # Build home - body
        body_layout = QtWidgets.QVBoxLayout(home_body_widget)
        split_widget = QtWidgets.QSplitter(home_body_widget)
        split_widget.addWidget(assets_widget)
        split_widget.addWidget(tasks_widget)
        split_widget.addWidget(files_widget)
        split_widget.addWidget(side_panel)
        split_widget.setSizes([255, 160, 455, 175])

        body_layout.addWidget(split_widget)

        # Add top margin for tasks to align it visually with files as
        # the files widget has a filter field which tasks does not.
        tasks_widget.setContentsMargins(0, 32, 0, 0)

        # Set context after asset widget is refreshed
        # - to do so it is necessary to wait until refresh is done
        set_context_timer = QtCore.QTimer()
        set_context_timer.setInterval(100)

        # Connect signals
        set_context_timer.timeout.connect(self._on_context_set_timeout)
        assets_widget.selection_changed.connect(self._on_asset_changed)
        tasks_widget.task_changed.connect(self._on_task_changed)
        files_widget.file_selected.connect(self.on_file_select)
        files_widget.workfile_created.connect(self.on_workfile_create)
        files_widget.file_opened.connect(self._on_file_opened)
        files_widget.publish_file_viewed.connect(
            self._on_publish_file_viewed
        )
        files_widget.published_visible_changed.connect(
            self._on_published_change
        )
        side_panel.save_clicked.connect(self.on_side_panel_save)

        self._set_context_timer = set_context_timer
        self.home_page_widget = home_page_widget
        self.pages_widget = pages_widget
        self.home_body_widget = home_body_widget
        self.split_widget = split_widget

        self.assets_widget = assets_widget
        self.tasks_widget = tasks_widget
        self.files_widget = files_widget
        self.side_panel = side_panel

        # Force focus on the open button by default, required for Houdini.
        files_widget.setFocus()

        self.resize(1200, 600)

        self._first_show = True
        self._context_to_set = None

    def showEvent(self, event):
        super(Window, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.refresh()
            self.setStyleSheet(style.load_stylesheet())

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidentally perform Maya commands
        whilst trying to name an instance.

        """

    def set_save_enabled(self, enabled):
        self.files_widget.set_save_enabled(enabled)

    def on_file_select(self, filepath):
        asset_id = self.assets_widget.get_selected_asset_id()
        task_name = self.tasks_widget.get_selected_task_name()

        workfile_doc = None
        if asset_id and task_name and filepath:
            filename = os.path.split(filepath)[1]
            workfile_doc = get_workfile_doc(
                asset_id, task_name, filename, io
            )
        self.side_panel.set_context(
            asset_id, task_name, filepath, workfile_doc
        )

    def on_workfile_create(self, filepath):
        self._create_workfile_doc(filepath)

    def _on_file_opened(self):
        self.close()

    def _on_publish_file_viewed(self):
        self.side_panel.refresh_publish_temp_sizes()

    def _on_published_change(self, visible):
        self.side_panel.set_published_visible(visible)

    def on_side_panel_save(self):
        workfile_doc, data = self.side_panel.get_workfile_data()
        if not workfile_doc:
            filepath = self.files_widget._get_selected_filepath()
            self._create_workfile_doc(filepath, force=True)
            workfile_doc = self._get_current_workfile_doc()

        save_workfile_data_to_doc(workfile_doc, data, io)

    def _get_current_workfile_doc(self, filepath=None):
        if filepath is None:
            filepath = self.files_widget._get_selected_filepath()
        task_name = self.tasks_widget.get_selected_task_name()
        asset_id = self.assets_widget.get_selected_asset_id()
        if not task_name or not asset_id or not filepath:
            return

        filename = os.path.split(filepath)[1]
        return get_workfile_doc(
            asset_id, task_name, filename, io
        )

    def _create_workfile_doc(self, filepath, force=False):
        workfile_doc = None
        if not force:
            workfile_doc = self._get_current_workfile_doc(filepath)

        if not workfile_doc:
            workdir, filename = os.path.split(filepath)
            asset_id = self.assets_widget.get_selected_asset_id()
            asset_doc = io.find_one({"_id": asset_id})
            task_name = self.tasks_widget.get_selected_task_name()
            create_workfile_doc(asset_doc, task_name, filename, workdir, io)

    def refresh(self):
        # Refresh asset widget
        self.assets_widget.refresh()

        self._on_task_changed()

    def set_context(self, context):
        self._context_to_set = context
        self._set_context_timer.start()

    def _on_context_set_timeout(self):
        if self._context_to_set is None:
            self._set_context_timer.stop()
            return

        if self.assets_widget.refreshing:
            return

        self._context_to_set, context = None, self._context_to_set
        if "asset" in context:
            asset_doc = io.find_one(
                {
                    "name": context["asset"],
                    "type": "asset"
                },
                {"_id": 1}
            ) or {}
            asset_id = asset_doc.get("_id")
            # Select the asset
            self.assets_widget.select_asset(asset_id)
            self.tasks_widget.set_asset_id(asset_id)

        if "task" in context:
            self.tasks_widget.select_task_name(context["task"])
        self._on_task_changed()

    def _on_asset_changed(self):
        asset_id = self.assets_widget.get_selected_asset_id()
        if asset_id:
            self.tasks_widget.setEnabled(True)
        else:
            # Force disable the other widgets if no
            # active selection
            self.tasks_widget.setEnabled(False)
            self.files_widget.setEnabled(False)

        self.tasks_widget.set_asset_id(asset_id)

    def _on_task_changed(self):
        asset_id = self.assets_widget.get_selected_asset_id()
        task_name = self.tasks_widget.get_selected_task_name()
        task_type = self.tasks_widget.get_selected_task_type()

        asset_is_valid = asset_id is not None
        self.tasks_widget.setEnabled(asset_is_valid)

        self.files_widget.setEnabled(bool(task_name) and asset_is_valid)
        self.files_widget.set_asset_task(asset_id, task_name, task_type)
        self.files_widget.refresh()
