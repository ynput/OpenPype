from Qt import QtWidgets, QtCore
from openpype import style


class ButtonWithMenu(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super(ButtonWithMenu, self).__init__(parent)

        self.setObjectName("ButtonWithMenu")

        self.setPopupMode(self.MenuButtonPopup)
        menu = QtWidgets.QMenu(self)

        self.setMenu(menu)

        self._menu = menu
        self._actions = []

    def menu(self):
        return self._menu

    def clear_actions(self):
        if self._menu is not None:
            self._menu.clear()
        self._actions = []

    def add_action(self, action):
        self._actions.append(action)
        self._menu.addAction(action)

    def _on_action_trigger(self):
        action = self.sender()
        if action not in self._actions:
            return
        action.trigger()


class SearchComboBox(QtWidgets.QComboBox):
    """Searchable ComboBox with empty placeholder value as first value"""

    def __init__(self, parent):
        super(SearchComboBox, self).__init__(parent)

        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)

        combobox_delegate = QtWidgets.QStyledItemDelegate(self)
        self.setItemDelegate(combobox_delegate)

        completer = self.completer()
        completer.setCompletionMode(
            QtWidgets.QCompleter.PopupCompletion
        )
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

        completer_view = completer.popup()
        completer_view.setObjectName("CompleterView")
        completer_delegate = QtWidgets.QStyledItemDelegate(completer_view)
        completer_view.setItemDelegate(completer_delegate)
        completer_view.setStyleSheet(style.load_stylesheet())

        self._combobox_delegate = combobox_delegate

        self._completer_delegate = completer_delegate
        self._completer = completer

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
