import json
from Qt import QtWidgets, QtCore


class InstanceDetail(QtWidgets.QWidget):
    save_triggered = QtCore.Signal()

    def __init__(self, parent=None):
        super(InstanceDetail, self).__init__(parent)

        details_widget = QtWidgets.QPlainTextEdit(self)
        details_widget.setObjectName("SubsetManagerDetailsText")

        save_btn = QtWidgets.QPushButton("Save", self)

        self._block_changes = False
        self._editable = False
        self._item_id = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(details_widget, 1)
        layout.addWidget(save_btn, 0, QtCore.Qt.AlignRight)

        save_btn.clicked.connect(self._on_save_clicked)
        details_widget.textChanged.connect(self._on_text_change)

        self._details_widget = details_widget
        self._save_btn = save_btn

        self.set_editable(False)

    def _on_save_clicked(self):
        if self.is_valid():
            self.save_triggered.emit()

    def set_editable(self, enabled=True):
        self._editable = enabled
        self.update_state()

    def update_state(self, valid=None):
        editable = self._editable
        if not self._item_id:
            editable = False

        self._save_btn.setVisible(editable)
        self._details_widget.setReadOnly(not editable)
        if valid is None:
            valid = self.is_valid()

        self._save_btn.setEnabled(valid)
        self._set_invalid_detail(valid)

    def _set_invalid_detail(self, valid):
        state = ""
        if not valid:
            state = "invalid"

        current_state = self._details_widget.property("state")
        if current_state != state:
            self._details_widget.setProperty("state", state)
            self._details_widget.style().polish(self._details_widget)

    def set_details(self, container, item_id):
        self._item_id = item_id

        text = "Nothing selected"
        if item_id:
            try:
                text = json.dumps(container, indent=4)
            except Exception:
                text = str(container)

        self._block_changes = True
        self._details_widget.setPlainText(text)
        self._block_changes = False

        self.update_state()

    def instance_data_from_text(self):
        try:
            jsoned = json.loads(self._details_widget.toPlainText())
        except Exception:
            jsoned = None
        return jsoned

    def item_id(self):
        return self._item_id

    def is_valid(self):
        if not self._item_id:
            return True

        value = self._details_widget.toPlainText()
        valid = False
        try:
            jsoned = json.loads(value)
            if jsoned and isinstance(jsoned, dict):
                valid = True

        except Exception:
            pass
        return valid

    def _on_text_change(self):
        if self._block_changes or not self._item_id:
            return

        valid = self.is_valid()
        self.update_state(valid)
