from Qt import QtWidgets, QtCore
from .widgets import ExpandingWidget
from .inputs import ConfigObject, ModifiableDict, PathWidget, RawJsonWidget
from .lib import NOT_SET, TypeToKlass, CHILD_OFFSET


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
        self.key = "anatomy"

        self._child_state = None
        self._state = None

        self._any_parent_is_group = False

        self.root_widget = RootsWidget(self)
        self.templates_widget = TemplatesWidget(self)

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        body_widget = ExpandingWidget("Anatomy", self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(body_widget)

        content_widget = QtWidgets.QWidget(body_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        content_layout.setSpacing(5)

        content_layout.addWidget(self.root_widget)
        content_layout.addWidget(self.templates_widget)

        body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.label_widget = body_widget.label_widget

        self.root_widget.value_changed.connect(self._on_value_change)

    def update_default_values(self, parent_values):
        self._state = None
        self._child_state = None

        if isinstance(parent_values, dict):
            value = parent_values.get(self.key, NOT_SET)
        else:
            value = NOT_SET

        self.root_widget.update_default_values(value)
        self.templates_widget.update_default_values(value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._child_state = None

        if isinstance(parent_values, dict):
            value = parent_values.get(self.key, NOT_SET)
        else:
            value = NOT_SET

        self.root_widget.update_studio_values(value)
        self.templates_widget.update_studio_values(value)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None

        value = NOT_SET
        if parent_values is not NOT_SET:
            value = parent_values.get(self.key, value)

        self.root_widget.apply_overrides(value)
        self.templates_widget.apply_overrides(value)

    def set_value(self, value):
        raise TypeError("AnatomyWidget does not allow to use `set_value`")

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self.hierarchical_style_update()

        self.value_changed.emit(self)

    def update_style(self, is_overriden=None):
        child_has_studio_override = self.child_has_studio_override
        child_modified = self.child_modified
        child_invalid = self.child_invalid
        child_state = self.style_state(
            child_has_studio_override,
            child_invalid,
            self.child_overriden,
            child_modified
        )
        if child_state:
            child_state = "child-{}".format(child_state)

        if child_state != self._child_state:
            self.body_widget.side_line_widget.setProperty("state", child_state)
            self.body_widget.side_line_widget.style().polish(
                self.body_widget.side_line_widget
            )
            self._child_state = child_state

    def hierarchical_style_update(self):
        self.root_widget.hierarchical_style_update()
        self.templates_widget.hierarchical_style_update()
        self.update_style()

    @property
    def child_has_studio_override(self):
        return (
            self.root_widget.child_has_studio_override
            or self.templates_widget.child_has_studio_override
        )

    @property
    def child_modified(self):
        return (
            self.root_widget.child_modified
            or self.templates_widget.child_modified
        )

    @property
    def child_overriden(self):
        return (
            self.root_widget.child_overriden
            or self.templates_widget.child_overriden
        )

    @property
    def child_invalid(self):
        return (
            self.root_widget.child_invalid
            or self.templates_widget.child_invalid
        )

    def remove_overrides(self):
        self.root_widget.remove_overrides()
        self.templates_widget.remove_overrides()

    def discard_changes(self):
        self.root_widget.discard_changes()
        self.templates_widget.discard_changes()

    def overrides(self):
        return self.config_value(), True

    def item_value(self):
        output = {}
        output.update(self.root_widget.config_value())
        output.update(self.templates_widget.config_value())
        return output

    def config_value(self):
        return {self.key: self.item_value()}


class RootsWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)

    def __init__(self, parent):
        super(RootsWidget, self).__init__(parent)
        self.setObjectName("RootsWidget")
        self._parent = parent
        self.key = "roots"

        self._state = None
        self._multiroot_state = None

        self._is_group = True
        self._any_parent_is_group = False

        self.global_is_multiroot = False
        self.was_multiroot = NOT_SET

        checkbox_widget = QtWidgets.QWidget(self)
        multiroot_label = QtWidgets.QLabel(
            "Use multiple roots", checkbox_widget
        )
        multiroot_checkbox = QtWidgets.QCheckBox(checkbox_widget)

        checkbox_layout = QtWidgets.QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(multiroot_label, 0)
        checkbox_layout.addWidget(multiroot_checkbox, 1)

        body_widget = ExpandingWidget("Roots", self)
        content_widget = QtWidgets.QWidget(body_widget)

        path_widget_data = {
            "key": "roots",
            "multipath": False,
            "multiplatform": True
        }
        singleroot_widget = PathWidget(
            path_widget_data, self,
            as_widget=True, parent_widget=content_widget
        )
        multiroot_data = {
            "key": "roots",
            "object_type": "path-widget",
            "expandable": False,
            "input_modifiers": {
                "multiplatform": True
            }
        }
        multiroot_widget = ModifiableDict(
            multiroot_data, self,
            as_widget=True, parent_widget=content_widget
        )

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(checkbox_widget)
        content_layout.addWidget(singleroot_widget)
        content_layout.addWidget(multiroot_widget)

        body_widget.set_content_widget(content_widget)
        self.label_widget = body_widget.label_widget

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(body_widget)

        self.body_widget = body_widget
        self.multiroot_label = multiroot_label
        self.multiroot_checkbox = multiroot_checkbox
        self.singleroot_widget = singleroot_widget
        self.multiroot_widget = multiroot_widget

        multiroot_checkbox.stateChanged.connect(self._on_multiroot_checkbox)
        singleroot_widget.value_changed.connect(self._on_value_change)
        multiroot_widget.value_changed.connect(self._on_value_change)

        self._on_multiroot_checkbox()

    @property
    def is_multiroot(self):
        return self.multiroot_checkbox.isChecked()

    def update_default_values(self, parent_values):
        self._state = None
        self._multiroot_state = None

        if isinstance(parent_values, dict):
            value = parent_values.get(self.key, NOT_SET)
        else:
            value = NOT_SET

        is_multiroot = False
        if isinstance(value, dict):
            for _value in value.values():
                if isinstance(_value, dict):
                    is_multiroot = True
                    break

        self.global_is_multiroot = is_multiroot
        self.was_multiroot = is_multiroot
        self.set_multiroot(is_multiroot)

        if is_multiroot:
            for _value in value.values():
                singleroot_value = _value
                break

            multiroot_value = value
        else:
            singleroot_value = value
            multiroot_value = {"": value}

        self.singleroot_widget.update_default_values(singleroot_value)
        self.multiroot_widget.update_default_values(multiroot_value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._multiroot_state = None

        if isinstance(parent_values, dict):
            value = parent_values.get(self.key, NOT_SET)
        else:
            value = NOT_SET

        is_multiroot = False
        if isinstance(value, dict):
            for _value in value.values():
                if isinstance(_value, dict):
                    is_multiroot = True
                    break

        self.global_is_multiroot = is_multiroot
        self.was_multiroot = is_multiroot
        self.set_multiroot(is_multiroot)

        if value is NOT_SET:
            self._has_studio_override = False
            self._had_studio_override = False
        else:
            self._has_studio_override = True
            self._had_studio_override = True

        if is_multiroot:
            self.singleroot_widget.update_studio_values(NOT_SET)
            self.multiroot_widget.update_studio_values(value)
        else:
            self.singleroot_widget.update_studio_values(value)
            self.multiroot_widget.update_studio_values(NOT_SET)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._multiroot_state = None
        self._is_modified = False

        value = NOT_SET
        if parent_values is not NOT_SET:
            value = parent_values.get(self.key, value)

        if value is NOT_SET:
            is_multiroot = self.global_is_multiroot
        else:
            is_multiroot = False
            if isinstance(value, dict):
                for _value in value.values():
                    if isinstance(_value, dict):
                        is_multiroot = True
                        break

        self.was_multiroot = is_multiroot
        self.set_multiroot(is_multiroot)

        if is_multiroot:
            self._is_overriden = parent_values is not NOT_SET
            self._was_overriden = bool(self._is_overriden)
            self.singleroot_widget.apply_overrides(NOT_SET)
            self.multiroot_widget.apply_overrides(parent_values)
        else:
            self._is_overriden = value is not NOT_SET
            self._was_overriden = bool(self._is_overriden)
            self.singleroot_widget.apply_overrides(value)
            self.multiroot_widget.apply_overrides(NOT_SET)

    def hierarchical_style_update(self):
        self.singleroot_widget.hierarchical_style_update()
        self.multiroot_widget.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        multiroot_state = self.style_state(
            self.has_studio_override,
            False,
            self.is_overriden,
            self.was_multiroot != self.is_multiroot
        )
        if multiroot_state != self._multiroot_state:
            self.multiroot_label.setProperty("state", multiroot_state)
            self.multiroot_label.style().polish(self.multiroot_label)
            self._multiroot_state = multiroot_state

        state = self.style_state(
            self.has_studio_override,
            self.is_invalid,
            self.is_overriden,
            self.is_modified
        )
        if self._state == state:
            return

        if state:
            child_state = "child-{}".format(state)
        else:
            child_state = ""

        self.body_widget.side_line_widget.setProperty("state", child_state)
        self.body_widget.side_line_widget.style().polish(
            self.body_widget.side_line_widget
        )

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

        self._state = state

    def _on_multiroot_checkbox(self):
        self.set_multiroot(self.is_multiroot)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if item is not None and (
            (self.is_multiroot and item != self.multiroot_widget)
            or (not self.is_multiroot and item != self.singleroot_widget)
        ):
            return

        if self.is_group and self.is_overidable:
            self._is_overriden = True

        self._is_modified = (
            self.was_multiroot != self.is_multiroot
            or self.child_modified
        )

        self.value_changed.emit(self)

    def set_multiroot(self, is_multiroot=None):
        if is_multiroot is None:
            is_multiroot = not self.is_multiroot

        if is_multiroot != self.is_multiroot:
            self.multiroot_checkbox.setChecked(is_multiroot)

        self.singleroot_widget.setVisible(not is_multiroot)
        self.multiroot_widget.setVisible(is_multiroot)

        self._on_value_change()

    @property
    def child_has_studio_override(self):
        if self.is_multiroot:
            return self.multiroot_widget.child_has_studio_override
        else:
            return self.singleroot_widget.child_has_studio_override

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

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False

        self.set_multiroot(self.global_is_multiroot)

        self.singleroot_widget.remove_overrides()
        self.multiroot_widget.remove_overrides()

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._is_modified = False
        if self._is_overriden:
            self.set_multiroot(self.was_multiroot)
        else:
            self.set_multiroot(self.global_is_multiroot)

        self.singleroot_widget.discard_changes()
        self.multiroot_widget.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        self._is_overriden = self._was_overriden
        self.singleroot_widget.set_as_overriden()
        self.multiroot_widget.set_as_overriden()

    def item_value(self):
        if self.is_multiroot:
            return self.multiroot_widget.item_value()
        else:
            return self.singleroot_widget.item_value()

    def config_value(self):
        return {self.key: self.item_value()}


class TemplatesWidget(QtWidgets.QWidget, ConfigObject):
    def __init__(self, parent):
        super(TemplatesWidget, self).__init__(parent)

        self._parent = parent

        self._state = None

        self._is_group = True
        self._any_parent_is_group = False
        self.key = "templates"

        body_widget = ExpandingWidget("Templates", self)
        content_widget = QtWidgets.QWidget(body_widget)
        body_widget.set_content_widget(content_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)

        template_input_data = {
            "key": self.key
        }
        self.body_widget = body_widget
        self.label_widget = body_widget.label_widget
        self.value_input = RawJsonWidget(
            template_input_data, self,
            label_widget=self.label_widget
        )
        content_layout.addWidget(self.value_input)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(body_widget)

    def update_default_values(self, values):
        self._state = None
        self.value_input.update_default_values(values)

    def update_studio_values(self, values):
        self._state = None
        self.value_input.update_studio_values(values)

    def apply_overrides(self, parent_values):
        self._state = None
        self.value_input.apply_overrides(parent_values)

    def hierarchical_style_update(self):
        self.value_input.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        state = self.style_state(
            self.has_studio_override,
            self.child_invalid,
            self.child_overriden,
            self.child_modified
        )
        if self._state == state:
            return

        if state:
            child_state = "child-{}".format(state)
        else:
            child_state = ""
        print(child_state)
        self.body_widget.side_line_widget.setProperty("state", child_state)
        self.body_widget.side_line_widget.style().polish(
            self.body_widget.side_line_widget
        )

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

        self._state = state

    @property
    def is_modified(self):
        return self.value_input.is_modified

    @property
    def is_overriden(self):
        return self._is_overriden

    @property
    def child_has_studio_override(self):
        return self.value_input.child_has_studio_override

    @property
    def child_modified(self):
        return self.value_input.child_modified

    @property
    def child_overriden(self):
        return self.value_input.child_overriden

    @property
    def child_invalid(self):
        return self.value_input.child_invalid

    def remove_overrides(self):
        self.value_input.remove_overrides()

    def discard_changes(self):
        self.value_input.discard_changes()

    def set_as_overriden(self):
        self.value_input.set_as_overriden()

    def overrides(self):
        if not self.child_overriden:
            return NOT_SET, False
        return self.config_value(), True

    def item_value(self):
        return self.value_input.item_value()

    def config_value(self):
        return self.value_input.config_value()


TypeToKlass.types["anatomy"] = AnatomyWidget
