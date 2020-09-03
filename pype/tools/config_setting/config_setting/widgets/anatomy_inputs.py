from Qt import QtWidgets, QtCore
from .widgets import ExpandingWidget
from .inputs import ConfigObject, ModifiableDict, PathWidget
from .lib import NOT_SET, TypeToKlass


class AnatomyWidget(QtWidgets.QWidget, ConfigObject):
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
        if as_widget:
            raise TypeError(
                "`AnatomyWidget` does not allow to be used as widget."
            )
        super(AnatomyWidget, self).__init__(parent)
        self.setObjectName("AnatomyWidget")
        self._parent = parent

        self._child_state = None
        self._state = None

        self._is_group = True

        self.key = "anatomy"

        self.override_value = NOT_SET
        self.start_value = NOT_SET
        self.global_value = NOT_SET

        self.root_keys = None
        self.root_widget = RootsWidget(self)
        self.templates_widget = TemplatesWidget(self)

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        body_widget = ExpandingWidget("Anatomy", self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 0, 5)
        layout.setSpacing(0)
        layout.addWidget(body_widget)

        content_widget = QtWidgets.QWidget(body_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)

        content_layout.addWidget(self.root_widget)
        content_layout.addWidget(self.templates_widget)

        body_widget.set_content_widget(content_widget)

        self.label_widget = body_widget.label_widget

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

    def update_style(self, is_overriden=None):
        print("* update_style")
        child_modified = self.child_modified
        child_invalid = self.child_invalid
        child_state = self.style_state(
            child_invalid, self.child_overriden, child_modified
        )
        if child_state:
            child_state = "child-{}".format(child_state)

        if child_state != self._child_state:
            self.setProperty("state", child_state)
            self.style().polish(self)
            self._child_state = child_state

        state = self.style_state(
            child_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

        self._state = state

    def hierarchical_style_update(self):
        self.root_widget.hierarchical_style_update()
        self.templates_widget.hierarchical_style_update()
        self.update_style()

    @property
    def is_modified(self):
        return self._is_modified or self.child_modified

    @property
    def child_modified(self):
        return (
            self.root_widget.child_modified
            or self.templates_widget.child_modified
        )

    @property
    def child_overriden(self):
        return (
            self.root_widget.is_overriden
            or self.root_widget.child_overriden
            or self.templates_widget.is_overriden
            or self.templates_widget.child_overriden
        )

    @property
    def child_invalid(self):
        return (
            self.root_widget.child_invalid
            or self.templates_widget.child_invalid
        )

    def item_value(self):
        print("* item_value")


class RootsWidget(QtWidgets.QWidget, ConfigObject):
    multiroot_changed = QtCore.Signal()

    def __init__(self, parent):
        super(RootsWidget, self).__init__(parent)
        self.setObjectName("RootsWidget")
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
            "expandable": False,
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

        self._on_multiroot_checkbox()

    @property
    def is_multiroot(self):
        return self.multiroot_checkbox.isChecked()

    def update_global_values(self, values):
        self.singleroot_widget.update_global_values(values)
        self.multiroot_widget.update_global_values(values)

    def hierarchical_style_update(self):
        self.singleroot_widget.hierarchical_style_update()
        self.multiroot_widget.hierarchical_style_update()

    def _on_multiroot_checkbox(self):
        self.set_multiroot(self.is_multiroot)

    def set_multiroot(self, is_multiroot=None):
        if is_multiroot is None:
            is_multiroot = not self.is_multiroot

        if is_multiroot != self.is_multiroot:
            self.multiroot_checkbox.setChecked(is_multiroot)

        self.singleroot_widget.setVisible(not is_multiroot)
        self.multiroot_widget.setVisible(is_multiroot)

        self.multiroot_changed.emit()

    @property
    def is_modified(self):
        return self._is_modified or self.child_modified

    @property
    def is_overriden(self):
        return self._is_overriden

    @property
    def child_modified(self):
        if self.is_multiroot:
            return self.multiroot_widget.child_modified
        else:
            return self.singleroot_widget.child_modified

    @property
    def child_overriden(self):
        if self.is_multiroot:
            return (
                self.multiroot_widget.is_overriden
                or self.multiroot_widget.child_overriden
            )
        else:
            return (
                self.singleroot_widget.is_overriden
                or self.singleroot_widget.child_overriden
            )

    @property
    def child_invalid(self):
        if self.is_multiroot:
            return self.multiroot_widget.child_invalid
        else:
            return self.singleroot_widget.child_invalid


class TemplatesWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(TemplatesWidget, self).__init__(parent)

    def update_global_values(self, values):
        pass

    def hierarchical_style_update(self):
        pass

    @property
    def is_modified(self):
        return False

    @property
    def is_overriden(self):
        return False

    @property
    def child_modified(self):
        return False

    @property
    def child_overriden(self):
        return False

    @property
    def child_invalid(self):
        return False


TypeToKlass.types["anatomy"] = AnatomyWidget
