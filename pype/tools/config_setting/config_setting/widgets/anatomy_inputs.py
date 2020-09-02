from Qt import QtWidgets, QtCore
from .inputs import InputObject
from .lib import NOT_SET, TypeToKlass


class AnatomyWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)
    template_keys = (
        "project[name]",
        "project[code]",
        "asset",
        "task",
        "subset",
        "family",
        "version",
        "ext",
        "representation"
    )
    default_exmaple_data = {
        "project": {
            "name": "ProjectPype",
            "code": "pp",
        },
        "asset": "sq01sh0010",
        "task": "compositing",
        "subset": "renderMain",
        "family": "render",
        "version": 1,
        "ext": ".png",
        "representation": "png"
    }

    def __init__(
        self, input_data, parent, as_widget=False, label_widget=None
    ):
        super(AnatomyWidget, self).__init__(parent)

        self._parent = parent
        self._as_widget = as_widget

        self._is_group = True

        self.key = "anatomy"

        self.override_value = NOT_SET
        self.start_value = NOT_SET
        self.global_value = NOT_SET

        self.root_keys = None
        self.root_widget = RootsWidget(self)
        self.templates_widget = TemplatesWidget(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label = QtWidgets.QLabel("Anatomy", self)
        layout.addWidget(label)
        layout.addWidget(self.root_widget)
        layout.addWidget(self.templates_widget)

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


class RootsWidget(QtWidgets.QWidget):
    multiroot_changed = QtCore.QSignal()

    def __init__(self, parent=None):
        super(RootsWidget, self).__init__(parent)

        self.root_keys = None

        layout = QtWidgets.QHBoxLayout(self)
        multiroot_checkbox = QtWidgets.QCheckBox(self)
        layout.addWidget(multiroot_checkbox)

        self.multiroot_checkbox = multiroot_checkbox
        multiroot_checkbox.stateChanged.connect(self._on_multiroot_checkbox)

    def _on_multiroot_checkbox(self):
        self.set_multiroot(self.multiroot_checkbox.isChecked())

    def set_multiroot(self, is_multiroot=None):
        if is_multiroot is None:
            is_multiroot = not self.multiroot_checkbox.isChecked()

        if is_multiroot != self.multiroot_checkbox.isChecked():
            self.multiroot_checkbox.setChecked(is_multiroot)

        self.multiroot_changed.emit()


class TemplatesWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(TemplatesWidget, self).__init__(parent)


TypeToKlass.types["anatomy"] = AnatomyWidget
