import os
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
    save_clicked = QtCore.Signal()
    published_workfile_message = (
        "<b>INFO</b>: Opened published workfiles will be stored in"
        " temp directory on your machine. Current temp size: <b>{}</b>."
    )

    def __init__(self, control, parent=None):
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

        control.register_event_callback(
            "selection.path.changed", self._on_selection_change
        )

        self._details_input = details_input
        self._artist_note_widget = artist_note_widget
        self._note_input = note_input
        self._btn_note_save = btn_note_save

        self._orig_note = ""
        self._workfile_doc = None

    def set_published_visible(self, published_visible):
        self._artist_note_widget.setVisible(not published_visible)

    def _on_selection_change(self, event):
        # TODO implement
        # self.set_context(folder_id, task_name, filepath, workfile_doc)
        pass

    def _on_note_change(self):
        text = self._note_input.toPlainText()
        self._btn_note_save.setEnabled(self._orig_note != text)

    def _on_save_click(self):
        self._orig_note = self._note_input.toPlainText()
        self._on_note_change()
        self.save_clicked.emit()

    def set_context(self, folder_id, task_name, filepath, workfile_doc):
        # Check if folder, task and file are selected
        # NOTE workfile document is not requirement
        enabled = bool(folder_id) and bool(task_name) and bool(filepath)

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