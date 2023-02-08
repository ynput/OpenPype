from qtpy import QtWidgets

from .widgets import AttributeDefinitionsWidget


class AttributeDefinitionsDialog(QtWidgets.QDialog):
    def __init__(self, attr_defs, parent=None):
        super(AttributeDefinitionsDialog, self).__init__(parent)

        attrs_widget = AttributeDefinitionsWidget(attr_defs, self)

        btns_widget = QtWidgets.QWidget(self)
        ok_btn = QtWidgets.QPushButton("OK", btns_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn, 0)
        btns_layout.addWidget(cancel_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(attrs_widget, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(btns_widget, 0)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        self._attrs_widget = attrs_widget

    def get_values(self):
        return self._attrs_widget.current_value()
