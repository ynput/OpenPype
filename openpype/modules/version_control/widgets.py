
import collections
import Qt.QtCore as QtCore  # type: ignore
import Qt.QtWidgets as QtWidgets  # type: ignore


class VersionControlLabel(QtWidgets.QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent=parent)
        self.setText(text)
        self.setObjectName("VersionControlLabel")
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Maximum)


class VersionControlTextEdit(QtWidgets.QPlainTextEdit):
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent=parent)
        self.setPlaceholderText(placeholder_text)
        self.setObjectName("VersionControlTextEdit")
        self._valid = "invalid"

    @QtCore.Property(str)
    def valid(self):
        # type: () -> str
        return self._valid

    @valid.setter
    def valid(self, value):
        # type: (str) -> None
        update = self._valid != value
        self._valid = value
        if not update:
            return

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class VersionControlCommentWidget(QtWidgets.QWidget):
    # Signals:
    textChanged = QtCore.Signal(str)
    textIsValid = QtCore.Signal(bool)
    returnPressed = QtCore.Signal()

    text_changed = textChanged
    text_is_valid = textIsValid

    def __init__(self, parent=None):
        super(VersionControlCommentWidget, self).__init__(parent=parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Maximum)

        self.setObjectName("VersionControlCommentWidget")
        self._character_count = 25
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        text_edit = VersionControlTextEdit(
            "Enter a detailed comment to submit", self
        )

        characters_to_go_text = "<b>Characters Required:</b> {}"
        characters_to_go_label = VersionControlLabel(
            text=characters_to_go_text.format(self._character_count),
            parent=self
        )

        output_text = "<b>Comment Output:</b> {}"
        output_text_label = VersionControlLabel(
            text=output_text.format("Invalid"),
            parent=self
        )
        output_text_label.setWordWrap(True)
        self.style().unpolish(output_text_label)
        self.style().polish(output_text_label)
        output_text_label.update()

        layout.addWidget(text_edit)
        layout.addWidget(characters_to_go_label)
        layout.addWidget(output_text_label)

        text_update_timer = QtCore.QTimer()
        text_update_timer.setInterval(200)
        text_update_timer.timeout.connect(self._on_text_update_timer_timeout)

        text_edit.textChanged.connect(self._on_text_edit_text_changed)

        self._text_edit = text_edit
        self._characters_to_go_label = characters_to_go_label
        self._output_text_label = output_text_label
        self._output_text = output_text
        self._characters_to_go_text = characters_to_go_text
        self._text_update_timer = text_update_timer

        self._previous_heights = collections.defaultdict(lambda: 0)  # type: collections.defaultdict[str, int]
        self._vc_api = None

        self._adjust_ui_height()

    # Slots:
    @property
    def vc_api(self):
        """
        Version Control api module
        """
        if self._vc_api is None:
            import openpype.modules.version_control.api as api
            self._vc_api = api

        return self._vc_api

    @QtCore.Slot()
    def _on_text_update_timer_timeout(self):
        # type: () -> None
        self._text_changed()
        self._text_update_timer.stop()

    @QtCore.Slot()
    def _on_text_edit_text_changed(self):
        # type: () -> None
        if self._text_update_timer.isActive():
            self._text_update_timer.stop()

        self._text_update_timer.start()
        self._adjust_ui_height()

    # Private Methods:
    def _text_changed(self):
        # type: () -> None
        text = self._text_edit.toPlainText()
        text_length = len(text)
        valid_length = text_length >= self._character_count
        charactes_to_go = 0 if valid_length else self._character_count - text_length
        label_text = self._characters_to_go_text.format(charactes_to_go)
        self._characters_to_go_label.setText(label_text)
        self.textIsValid.emit(valid_length)
        self.textChanged.emit(text)
        self._text_edit.valid = "valid" if valid_length else "invalid"
        _text = (
            self.vc_api.get_change_list_description_with_tags(text)
            if valid_length
            else "Invalid"
        )
        self._output_text_label.setText(self._output_text.format(_text))

    def _adjust_widget_height_to_fit_text(self, widget, text):
        # type: (QtWidgets.QWidget, str) -> bool
        font_metrics = widget.fontMetrics()
        text = text or "Test String"
        line_count = len(text.splitlines()) + 1
        bounding_rect = font_metrics.boundingRect(text)
        contents_margins = widget.contentsMargins()
        widget_width = widget.width()
        if widget_width:
            word_wrap_count = abs(int((bounding_rect.width() / widget_width) - 1))
            line_count += word_wrap_count

        new_height = (
            (bounding_rect.height() * line_count) + contents_margins.top() + contents_margins.bottom()
        )
        previous_height = self._previous_heights[str(widget)]
        if new_height != previous_height:
            widget.setFixedHeight(new_height)
            self._previous_heights[str(widget)] = new_height
            return True

        return False

    def _adjust_text_edit_height(self):
        if self._adjust_widget_height_to_fit_text(
            self._text_edit, self._text_edit.toPlainText()
        ):
            self._text_edit.verticalScrollBar().setValue(0)
            self._text_edit.ensureCursorVisible()

    def _adjust_label_height(self):
        self._adjust_widget_height_to_fit_text(
            self._output_text_label, self._output_text_label.text()
        )

    def _adjust_ui_height(self):
        self._adjust_text_edit_height()
        self._adjust_label_height()

    # Public Methods:
    def text(self):
        # type: () -> str

        return self._text_edit.toPlainText()

    def setText(self, text):
        # type: (str | None) -> None

        text = text or ""
        self._text_edit.setPlainText(text)

    # Qt Override Methods:
    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.returnPressed.emit()

        return super().keyPressEvent(event)
