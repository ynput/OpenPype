from Qt import QtWidgets, QtCore
from .inputs import InputObject
from .lib import NOT_SET, AS_WIDGET, TypeToKlass


class AnatomyWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self._is_group = True
        self._state = None

        self.key = "anatomy"
        self.start_value = None

        super(AnatomyWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QtWidgets.QLabel("Test")
        layout.addWidget(label)

        self.override_value = NOT_SET

    def update_global_values(self, values):
        print("* update_global_values")

    def set_value(self, value, *, global_value=False):
        print("* set_value")

    def clear_value(self):
        print("* clear_value")

    def _on_value_change(self, item=None):
        print("* _on_value_change")

    def update_style(self):
        print("* update_style")

    def item_value(self):
        print("* item_value")


class TemplatesWidget:
    pass




TypeToKlass.types["anatomy"] = AnatomyWidget
