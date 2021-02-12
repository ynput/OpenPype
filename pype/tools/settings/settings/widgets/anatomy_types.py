from Qt import QtWidgets, QtCore
from .widgets import ExpandingWidget
from .item_types import (
    SettingObject,
    ModifiableDict,
    PathWidget,
    RawJsonWidget,
    DictWidget
)
from .lib import NOT_SET, TypeToKlass, CHILD_OFFSET, METADATA_KEY


class AnatomyWidget(QtWidgets.QWidget, SettingObject):
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

    def __init__(self, schema_data, parent, as_widget=False):
        if as_widget:
            raise TypeError(
                "`AnatomyWidget` does not allow to be used as widget."
            )
        super(AnatomyWidget, self).__init__(parent)
        self.setObjectName("AnatomyWidget")

        self.initial_attributes(schema_data, parent, as_widget)

        self.input_fields = []

        self.key = schema_data["key"]

    def create_ui(self, label_widget=None):
        children_data = self.schema_data["children"]
        for schema_data in children_data:
            item = TypeToKlass.types[schema_data["type"]](schema_data, self)
            item.create_ui()
            self.input_fields.append(item)

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

        for input_field in self.input_fields:
            content_layout.addWidget(input_field)
            input_field.value_changed.connect(self._on_value_change)

        body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.label_widget = body_widget.label_widget

    def update_default_values(self, parent_values):
        self._state = None
        self._child_state = None

        if isinstance(parent_values, dict):
            value = parent_values.get(self.key, NOT_SET)
        else:
            value = NOT_SET

        for input_field in self.input_fields:
            input_field.update_default_values(value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._child_state = None

        if isinstance(parent_values, dict):
            value = parent_values.get(self.key, NOT_SET)
        else:
            value = NOT_SET

        for input_field in self.input_fields:
            input_field.update_studio_values(value)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None

        value = NOT_SET
        if parent_values is not NOT_SET:
            value = parent_values.get(self.key, value)

        for input_field in self.input_fields:
            input_field.apply_overrides(value)

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
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

        self.update_style()

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if input_field.child_has_studio_override:
                return True
        return False

    @property
    def child_modified(self):
        for input_field in self.input_fields:
            if input_field.child_modified:
                return True
        return False

    @property
    def child_overriden(self):
        for input_field in self.input_fields:
            if input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def set_as_overriden(self):
        for input_field in self.input_fields:
            input_field.child_invalid.set_as_overriden()

    def remove_overrides(self):
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

    def discard_changes(self):
        for input_field in self.input_fields:
            input_field.discard_changes()

    def overrides(self):
        if self.child_overriden:
            return self.config_value(), True
        return NOT_SET, False

    def item_value(self):
        output = {}
        for input_field in self.input_fields:
            output.update(input_field.config_value())
        return output

    def studio_overrides(self):
        has_overrides = False
        for input_field in self.input_fields:
            if input_field.child_has_studio_override:
                has_overrides = True
                break

        if not has_overrides:
            return NOT_SET, False

        groups = []
        for input_field in self.input_fields:
            groups.append(input_field.key)

        value = self.config_value()
        if METADATA_KEY not in value[self.key]:
            value[self.key][METADATA_KEY] = {}
        value[self.key][METADATA_KEY]["groups"] = groups

        return value, True

    def config_value(self):
        return {self.key: self.item_value()}


class RootsWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)

    def __init__(self, input_data, parent):
        super(RootsWidget, self).__init__(parent)
        self.setObjectName("RootsWidget")

        input_data["is_group"] = True
        self.initial_attributes(input_data, parent, False)

        self.key = input_data["key"]

        self.was_multiroot = NOT_SET

    def create_ui(self, _label_widget=None):
        body_widget = ExpandingWidget("Roots", self)
        content_widget = QtWidgets.QWidget(body_widget)

        multiroot_data = {
            "key": self.key,
            "expandable": False,
            "object_type": {
                "type": "path-widget",
                "multiplatform": True
            }
        }
        multiroot_widget = ModifiableDict(
            multiroot_data, self,
            as_widget=True, parent_widget=content_widget
        )
        multiroot_widget.create_ui()

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(multiroot_widget)

        body_widget.set_content_widget(content_widget)
        self.label_widget = body_widget.label_widget

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(body_widget)

        self.body_widget = body_widget
        self.multiroot_widget = multiroot_widget
        multiroot_widget.value_changed.connect(self._on_value_change)

    def update_default_values(self, parent_values):
        self._state = None
        self._is_modified = False

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

        self._has_studio_override = False
        self._had_studio_override = False

        if not is_multiroot and value is not NOT_SET:
            value = {"": value}

        self.multiroot_widget.update_default_values(value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._is_modified = False

        if isinstance(parent_values, dict):
            value = parent_values.get(self.key, NOT_SET)
        else:
            value = NOT_SET

        self._has_studio_override = value is not NOT_SET
        self._had_studio_override = value is not NOT_SET

        self.multiroot_widget.update_studio_values(value)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._is_modified = False

        value = NOT_SET
        if parent_values is not NOT_SET:
            value = parent_values.get(self.key, value)

        self._is_overriden = value is not NOT_SET
        self._was_overriden = bool(self._is_overriden)
        self.multiroot_widget.apply_overrides(value)

    def hierarchical_style_update(self):
        self.multiroot_widget.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        state = self.style_state(
            self.has_studio_override,
            self.child_invalid,
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

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group and self.is_overidable:
            self._is_overriden = True

        self._is_modified = bool(self.child_modified)

        self.update_style()

        self.value_changed.emit(self)

    @property
    def child_has_studio_override(self):
        return self.multiroot_widget.has_studio_override

    @property
    def child_modified(self):
        return self.multiroot_widget.child_modified

    @property
    def child_overriden(self):
        return (
            self.multiroot_widget.is_overriden
            or self.multiroot_widget.child_overriden
        )

    @property
    def child_invalid(self):
        return self.multiroot_widget.child_invalid

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False

        self.multiroot_widget.remove_overrides()

    def reset_to_pype_default(self):
        self.multiroot_widget.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        self.multiroot_widget.reset_to_pype_default()
        self._has_studio_override = True

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._is_modified = False

        self.multiroot_widget.discard_changes()

        self._is_modified = self.child_modified
        self._has_studio_override = self._had_studio_override

    def set_as_overriden(self):
        self._is_overriden = True
        self.multiroot_widget.set_as_overriden()

    def item_value(self):
        return self.multiroot_widget.item_value()

    def config_value(self):
        return {self.key: self.item_value()}


class TemplatesWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)

    def __init__(self, input_data, parent):
        super(TemplatesWidget, self).__init__(parent)

        input_data["is_group"] = True
        self.initial_attributes(input_data, parent, False)

        self.key = input_data["key"]

    def create_ui(self, label_widget=None):
        body_widget = ExpandingWidget("Templates", self)
        content_widget = QtWidgets.QWidget(body_widget)
        body_widget.set_content_widget(content_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)

        template_input_data = {
            "key": self.key
        }
        self.body_widget = body_widget
        self.label_widget = body_widget.label_widget
        self.value_input = RawJsonWidget(template_input_data, self)
        self.value_input.create_ui(label_widget=self.label_widget)

        content_layout.addWidget(self.value_input)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(body_widget)

        self.value_input.value_changed.connect(self._on_value_change)

    def _on_value_change(self, item):
        self.update_style()

        self.value_changed.emit(self)

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
    def has_studio_override(self):
        return self.value_input._has_studio_override

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

    def reset_to_pype_default(self):
        self.value_input.reset_to_pype_default()

    def set_studio_default(self):
        self.value_input.set_studio_default()

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
TypeToKlass.types["anatomy_roots"] = RootsWidget
TypeToKlass.types["anatomy_templates"] = TemplatesWidget
