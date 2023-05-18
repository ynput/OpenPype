from qtpy import QtWidgets, QtCore
from openpype.tools.utils import set_style_property


class PublisherTabBtn(QtWidgets.QPushButton):
    tab_clicked = QtCore.Signal(str)

    def __init__(self, identifier, label, parent):
        super(PublisherTabBtn, self).__init__(label, parent)
        self._identifier = identifier
        self._active = False

        self.clicked.connect(self._on_click)

    def _on_click(self):
        self.tab_clicked.emit(self.identifier)

    @property
    def identifier(self):
        return self._identifier

    def activate(self):
        if self._active:
            return
        self._active = True
        set_style_property(self, "active", "1")

    def deactivate(self):
        if not self._active:
            return
        self._active = False
        set_style_property(self, "active", "")


class PublisherTabsWidget(QtWidgets.QFrame):
    tab_changed = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super(PublisherTabsWidget, self).__init__(parent)

        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.setSpacing(0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(btns_widget, 0)
        layout.addStretch(1)

        self._btns_layout = btns_layout

        self._current_identifier = None
        self._buttons_by_identifier = {}

    def is_current_tab(self, identifier):
        if isinstance(identifier, int):
            identifier = self.get_tab_by_index(identifier)

        if isinstance(identifier, PublisherTabBtn):
            identifier = identifier.identifier
        return self._current_identifier == identifier

    def add_tab(self, label, identifier):
        button = PublisherTabBtn(identifier, label, self)
        button.tab_clicked.connect(self._on_tab_click)
        self._btns_layout.addWidget(button, 0)
        self._buttons_by_identifier[identifier] = button

        if self._current_identifier is None:
            self.set_current_tab(identifier)
        return button

    def get_tab_by_index(self, index):
        if 0 >= index < self._btns_layout.count():
            item = self._btns_layout.itemAt(index)
            return item.widget()
        return None

    def set_current_tab(self, identifier):
        if isinstance(identifier, int):
            identifier = self.get_tab_by_index(identifier)

        if isinstance(identifier, PublisherTabBtn):
            identifier = identifier.identifier

        if identifier == self._current_identifier:
            return

        new_btn = self._buttons_by_identifier.get(identifier)
        if new_btn is None:
            return

        old_identifier = self._current_identifier
        old_btn = self._buttons_by_identifier.get(old_identifier)
        self._current_identifier = identifier

        if old_btn is not None:
            old_btn.deactivate()
        new_btn.activate()
        self.tab_changed.emit(old_identifier, identifier)

    def current_tab(self):
        return self._current_identifier

    def _on_tab_click(self, identifier):
        self.set_current_tab(identifier)
