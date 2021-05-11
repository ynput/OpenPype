import re
from .constants import (
    NAME_ALLOWED_SYMBOLS,
    NAME_REGEX
)
from Qt import QtWidgets, QtCore


class NameTextEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        super(NameTextEdit, self).__init__(*args, **kwargs)

        self.textChanged.connect(self._on_text_change)

    def _on_text_change(self, text):
        if NAME_REGEX.match(text):
            return

        idx = self.cursorPosition()
        before_text = text[0:idx]
        after_text = text[idx:len(text)]
        sub_regex = "[^{}]+".format(NAME_ALLOWED_SYMBOLS)
        new_before_text = re.sub(sub_regex, "", before_text)
        new_after_text = re.sub(sub_regex, "", after_text)
        idx -= (len(before_text) - len(new_before_text))

        self.setText(new_before_text + new_after_text)
        self.setCursorPosition(idx)


class FilterComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(FilterComboBox, self).__init__(parent)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setEditable(True)

        filter_proxy_model = QtCore.QSortFilterProxyModel(self)
        filter_proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        filter_proxy_model.setSourceModel(self.model())

        completer = QtWidgets.QCompleter(filter_proxy_model, self)
        completer.setCompletionMode(
            QtWidgets.QCompleter.UnfilteredPopupCompletion
        )
        self.setCompleter(completer)

        self.lineEdit().textEdited.connect(
            filter_proxy_model.setFilterFixedString
        )
        completer.activated.connect(self.on_completer_activated)

        self._completer = completer
        self._filter_proxy_model = filter_proxy_model

    def focusInEvent(self, event):
        super(FilterComboBox, self).focusInEvent(event)
        self.lineEdit().selectAll()

    def on_completer_activated(self, text):
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)

    def setModel(self, model):
        super(FilterComboBox, self).setModel(model)
        self._filter_proxy_model.setSourceModel(model)
        self._completer.setModel(self._filter_proxy_model)

    def setModelColumn(self, column):
        self._completer.setCompletionColumn(column)
        self._filter_proxy_model.setFilterKeyColumn(column)
        super(FilterComboBox, self).setModelColumn(column)
