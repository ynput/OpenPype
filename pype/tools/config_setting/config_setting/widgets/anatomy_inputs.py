from Qt import QtWidgets, QtCore
from .inputs import ConfigObject, InputObject, ModifiableDict, PathWidget
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

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label = QtWidgets.QLabel("Anatomy", self)
        layout.addWidget(label)
        layout.addWidget(self.root_widget)
        layout.addWidget(self.templates_widget)

    def update_global_values(self, values):
        print("* update_global_values")
        self.root_widget.update_global_values(values)
        self.templates_widget.update_global_values(values)

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


class RootsWidget(QtWidgets.QWidget, ConfigObject):
    multiroot_changed = QtCore.Signal()

    def __init__(self, parent):
        super(RootsWidget, self).__init__(parent)
        self._parent = parent
        self._is_group = True

        self.root_keys = None

        checkbox_widget = QtWidgets.QWidget(self)

        multiroot_label = QtWidgets.QLabel(
            "Use multiple roots", checkbox_widget
        )
        multiroot_checkbox = QtWidgets.QCheckBox(checkbox_widget)

        checkbox_layout = QtWidgets.QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(multiroot_label, 0)
        checkbox_layout.addWidget(multiroot_checkbox, 1)

        path_widget_data = {
            "key": "roots",
            "multiplatform": True,
            "label": "Roots"
        }
        singleroot_widget = PathWidget(path_widget_data, self)
        multiroot_data = {
            "key": "roots",
            "label": "Roots",
            "object_type": "path-widget",
            "input_modifiers": {
                "multiplatform": True
            }
        }
        multiroot_widget = ModifiableDict(multiroot_data, self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(checkbox_widget)
        main_layout.addWidget(singleroot_widget)
        main_layout.addWidget(multiroot_widget)

        self.multiroot_checkbox = multiroot_checkbox
        self.singleroot_widget = singleroot_widget
        self.multiroot_widget = multiroot_widget

        multiroot_checkbox.stateChanged.connect(self._on_multiroot_checkbox)

    def update_global_values(self, values):
        self.singleroot_widget.update_global_values(values)
        self.multiroot_widget.update_global_values(values)

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

    def update_global_values(self, values):
        pass


TypeToKlass.types["anatomy"] = AnatomyWidget
