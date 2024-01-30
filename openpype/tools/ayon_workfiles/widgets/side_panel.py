import datetime

from qtpy import QtWidgets, QtCore


def file_size_to_string(file_size):
    size = 0
    size_ending_mapping = {
        "KB": 1024 ** 1,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3
    }
    ending = "B"
    for _ending, _size in size_ending_mapping.items():
        if file_size < _size:
            break
        size = file_size / _size
        ending = _ending
    return "{:.2f} {}".format(size, ending)


class SidePanelWidget(QtWidgets.QWidget):
    """Details about selected workfile.

    Todos:
        At this moment only shows created and modified date of file
            or its size.

    Args:
        controller (AbstractWorkfilesFrontend): The control object.
        parent (QtWidgets.QWidget): The parent widget.
    """

    published_workfile_message = (
        "<b>INFO</b>: Opened published workfiles will be stored in"
        " temp directory on your machine. Current temp size: <b>{}</b>."
    )

    def __init__(self, controller, parent):
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

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(details_label, 0)
        main_layout.addWidget(details_input, 1)
        main_layout.addWidget(artist_note_widget, 1)

        note_input.textChanged.connect(self._on_note_change)
        btn_note_save.clicked.connect(self._on_save_click)

        controller.register_event_callback(
            "selection.workarea.changed", self._on_selection_change
        )

        self._details_input = details_input
        self._artist_note_widget = artist_note_widget
        self._note_input = note_input
        self._btn_note_save = btn_note_save

        self._folder_id = None
        self._task_id = None
        self._filepath = None
        self._orig_note = ""
        self._controller = controller

        self._set_context(None, None, None)

    def set_published_mode(self, published_mode):
        """Change published mode.

        Args:
            published_mode (bool): Published mode enabled.
        """

        self._artist_note_widget.setVisible(not published_mode)

    def _on_selection_change(self, event):
        folder_id = event["folder_id"]
        task_id = event["task_id"]
        filepath = event["path"]

        self._set_context(folder_id, task_id, filepath)

    def _on_note_change(self):
        text = self._note_input.toPlainText()
        self._btn_note_save.setEnabled(self._orig_note != text)

    def _on_save_click(self):
        note = self._note_input.toPlainText()
        self._controller.save_workfile_info(
            self._folder_id,
            self._task_id,
            self._filepath,
            note
        )
        self._orig_note = note
        self._btn_note_save.setEnabled(False)

    def _set_context(self, folder_id, task_id, filepath):
        workfile_info = None
        # Check if folder, task and file are selected
        if bool(folder_id) and bool(task_id) and bool(filepath):
            workfile_info = self._controller.get_workfile_info(
                folder_id, task_id, filepath
            )
        enabled = workfile_info is not None

        self._details_input.setEnabled(enabled)
        self._note_input.setEnabled(enabled)
        self._btn_note_save.setEnabled(enabled)

        self._folder_id = folder_id
        self._task_id = task_id
        self._filepath = filepath

        # Disable inputs and remove texts if any required arguments are
        #   missing
        if not enabled:
            self._orig_note = ""
            self._details_input.setPlainText("")
            self._note_input.setPlainText("")
            return

        note = workfile_info.note
        size_value = file_size_to_string(workfile_info.filesize)

        # Append html string
        datetime_format = "%b %d %Y %H:%M:%S"
        creation_time = datetime.datetime.fromtimestamp(
            workfile_info.creation_time)
        modification_time = datetime.datetime.fromtimestamp(
            workfile_info.modification_time)
        lines = (
            "<b>Size:</b>",
            size_value,
            "<b>Created:</b>",
            creation_time.strftime(datetime_format),
            "<b>Modified:</b>",
            modification_time.strftime(datetime_format)
        )
        self._orig_note = note
        self._note_input.setPlainText(note)

        # Set as empty string
        self._details_input.setPlainText("")
        self._details_input.appendHtml("<br>".join(lines))
