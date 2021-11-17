from Qt import QtWidgets, QtCore


class SearchComboBox(QtWidgets.QComboBox):
    """Searchable ComboBox with empty placeholder value as first value"""

    def __init__(self, parent=None):
        super(SearchComboBox, self).__init__(parent)

        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)

        # Apply completer settings
        completer = self.completer()
        completer.setCompletionMode(completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

        # Force style sheet on popup menu
        # It won't take the parent stylesheet for some reason
        # todo: better fix for completer popup stylesheet
        # if module.window:
        #     popup = completer.popup()
        #     popup.setStyleSheet(module.window.styleSheet())

    def set_placeholder(self, placeholder):
        self.lineEdit().setPlaceholderText(placeholder)

    def populate(self, items):
        self.clear()
        self.addItems([""])     # ensure first item is placeholder
        self.addItems(items)

    def get_valid_value(self):
        """Return the current text if it's a valid value else None

        Note: The empty placeholder value is valid and returns as ""

        """

        text = self.currentText()
        lookup = set(self.itemText(i) for i in range(self.count()))
        if text not in lookup:
            return None

        return text or None

    def set_valid_value(self, value):
        """Try to locate 'value' and pre-select it in dropdown."""
        index = self.findText(value)
        if index > -1:
            self.setCurrentIndex(index)
