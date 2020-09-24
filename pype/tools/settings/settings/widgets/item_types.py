import json
import collections
from Qt import QtWidgets, QtCore, QtGui
from .widgets import (
    ExpandingWidget,
    NumberSpinBox,
    PathInput,
    GridLabelWidget,
    ComboBox
)
from .multiselection_combobox import MultiSelectionComboBox
from .lib import NOT_SET, METADATA_KEY, TypeToKlass, CHILD_OFFSET
from pype.api import Logger
from avalon.vendor import qtawesome


class SettingObject:
    """Partially abstract class for Setting's item type workflow."""
    # `is_input_type` attribute says if has implemented item type methods
    is_input_type = True
    # Each input must have implemented default value for development
    # when defaults are not filled yet.
    default_input_value = NOT_SET
    # Will allow to show actions for the item type (disabled for proxies) else
    # item is skipped and try to trigger actions on it's parent.
    allow_actions = True
    # All item types must have implemented Qt signal which is emitted when
    # it's or it's children value has changed,
    value_changed = None
    # Item will expand to full width in grid layout
    expand_in_grid = False

    def _set_default_attributes(self):
        """Create and reset attributes required for all item types.

        They may not be used in the item but are required to be set.
        """
        # Default input attributes
        self._has_studio_override = False
        self._had_studio_override = False

        self._is_overriden = False
        self._was_overriden = False

        self._is_modified = False
        self._is_invalid = False

        self._is_nullable = False
        self._as_widget = False
        self._is_group = False

        self._any_parent_as_widget = None
        self._any_parent_is_group = None

        # Parent input
        self._parent = None

        # States of inputs
        self._state = None
        self._child_state = None

        # Attributes where values are stored
        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET

        # Log object
        self._log = None

        # Only for develop mode
        self.defaults_not_set = False

    def initial_attributes(self, input_data, parent, as_widget):
        """Prepare attributes based on entered arguments.

        This method should be same for each item type. Few item types
        may require to extend with specific attributes for their case.
        """
        self._set_default_attributes()

        self._parent = parent
        self._as_widget = as_widget

        self._is_group = input_data.get("is_group", False)
        # TODO not implemented yet
        self._is_nullable = input_data.get("is_nullable", False)

        any_parent_as_widget = parent.as_widget
        if not any_parent_as_widget:
            any_parent_as_widget = parent.any_parent_as_widget

        self._any_parent_as_widget = any_parent_as_widget

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self._any_parent_is_group = any_parent_is_group

    @property
    def develop_mode(self):
        """Tool is in develop mode or not.

        Returns:
            bool

        """
        return self._parent.develop_mode

    @property
    def log(self):
        """Auto created logger for debugging."""
        if self._log is None:
            self._log = Logger().get_logger(self.__class__.__name__)
        return self._log

    @property
    def had_studio_override(self):
        """Item had studio overrides on refresh.

        Use attribute `_had_studio_override` which should be changed only
        during methods `update_studio_values` and `update_default_values`.

        Returns:
            bool

        """
        return self._had_studio_override

    @property
    def has_studio_override(self):
        """Item has studio override at the moment.

        With combination of `had_studio_override` is possible to know if item
        is modified (not value change).

        Returns:
            bool

        """
        return self._has_studio_override or self._parent.has_studio_override

    @property
    def as_widget(self):
        """Item is used as widget in parent item.

        Returns:
            bool

        """
        return self._as_widget

    @property
    def any_parent_as_widget(self):
        """Any parent of item is used as widget.

        Attribute holding this information is set during creation and
        stored to `_any_parent_as_widget`.

        Why is this information useful: If any parent is used as widget then
        modifications and override are not important for whole part.

        Returns:
            bool

        """
        if self._any_parent_as_widget is None:
            return super(SettingObject, self).any_parent_as_widget
        return self._any_parent_as_widget

    @property
    def is_group(self):
        """Item represents key that can be overriden.

        Attribute `is_group` can be set to True only once in item hierarchy.

        Returns:
            bool

        """
        return self._is_group

    @property
    def any_parent_is_group(self):
        """Any parent of item is group.

        Attribute holding this information is set during creation and
        stored to `_any_parent_is_group`.

        Why is this information useful: If any parent is group and
        the parent is set as overriden, this item is overriden too.

        Returns:
            bool

        """
        if self._any_parent_is_group is None:
            return super(SettingObject, self).any_parent_is_group
        return self._any_parent_is_group

    @property
    def is_modified(self):
        """Has object any changes that require saving."""
        if self.any_parent_as_widget:
            return self._is_modified

        if self._is_modified or self.defaults_not_set:
            return True

        if self.is_overidable:
            return self.was_overriden != self.is_overriden
        else:
            return self.has_studio_override != self.had_studio_override

    @property
    def is_overriden(self):
        """Is object overriden so should be saved to overrides."""
        return self._is_overriden or self._parent.is_overriden

    @property
    def was_overriden(self):
        """Item had set value of project overrides on project change."""
        if self._as_widget:
            return self._parent.was_overriden
        return self._was_overriden

    @property
    def is_invalid(self):
        """Value set in is not valid."""
        return self._is_invalid

    @property
    def is_nullable(self):
        """Value of item can be set to None.

        NOT IMPLEMENTED!
        """
        return self._is_nullable

    @property
    def is_overidable(self):
        """ care about overrides."""

        return self._parent.is_overidable

    def any_parent_overriden(self):
        """Any of parent objects up to top hiearchy item is overriden.

        Returns:
            bool

        """

        if self._parent._is_overriden:
            return True
        return self._parent.any_parent_overriden()

    @property
    def ignore_value_changes(self):
        """Most of attribute changes are ignored on value change when True."""
        return self._parent.ignore_value_changes

    @ignore_value_changes.setter
    def ignore_value_changes(self, value):
        """Setter for global parent item to apply changes for all inputs."""
        self._parent.ignore_value_changes = value

    def config_value(self):
        """Output for saving changes or overrides."""
        return {self.key: self.item_value()}

    @classmethod
    def style_state(
        cls, has_studio_override, is_invalid, is_overriden, is_modified
    ):
        """Return stylesheet state by intered booleans."""
        items = []
        if is_invalid:
            items.append("invalid")
        else:
            if is_overriden:
                items.append("overriden")
            if is_modified:
                items.append("modified")

        if not items and has_studio_override:
            items.append("studio")

        return "-".join(items) or ""

    def show_actions_menu(self, event=None):
        if event and event.button() != QtCore.Qt.RightButton:
            return

        if not self.allow_actions:
            if event:
                return self.mouseReleaseEvent(event)
            return

        menu = QtWidgets.QMenu()

        actions_mapping = {}
        if self.child_modified:
            action = QtWidgets.QAction("Discard changes")
            actions_mapping[action] = self._discard_changes
            menu.addAction(action)

        if (
            self.is_overidable
            and not self.is_overriden
            and not self.any_parent_is_group
        ):
            action = QtWidgets.QAction("Set project override")
            actions_mapping[action] = self._set_as_overriden
            menu.addAction(action)

        if (
            not self.is_overidable
            and (
                self.has_studio_override
            )
        ):
            action = QtWidgets.QAction("Reset to pype default")
            actions_mapping[action] = self._reset_to_pype_default
            menu.addAction(action)

        if (
            not self.is_overidable
            and not self.is_overriden
            and not self.any_parent_is_group
            and not self._had_studio_override
        ):
            action = QtWidgets.QAction("Set studio default")
            actions_mapping[action] = self._set_studio_default
            menu.addAction(action)

        if (
            not self.any_parent_overriden()
            and (self.is_overriden or self.child_overriden)
        ):
            # TODO better label
            action = QtWidgets.QAction("Remove project override")
            actions_mapping[action] = self._remove_overrides
            menu.addAction(action)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def mouseReleaseEvent(self, event):
        if self.allow_actions and event.button() == QtCore.Qt.RightButton:
            return self.show_actions_menu()

        mro = type(self).mro()
        index = mro.index(self.__class__)
        item = None
        for idx in range(index + 1, len(mro)):
            _item = mro[idx]
            if hasattr(_item, "mouseReleaseEvent"):
                item = _item
                break

        if item:
            return item.mouseReleaseEvent(self, event)

    def _discard_changes(self):
        self.ignore_value_changes = True
        self.discard_changes()
        self.ignore_value_changes = False

    def discard_changes(self):
        """Item's implementation to discard all changes made by user.

        Reset all values to same values as had when opened GUI
        or when changed project.

        Must not affect `had_studio_override` value or `was_overriden`
        value. It must be marked that there are keys/values which are not in
        defaults or overrides.
        """
        raise NotImplementedError(
            "{} Method `discard_changes` not implemented!".format(
                repr(self)
            )
        )

    def _set_studio_default(self):
        self.ignore_value_changes = True
        self.set_studio_default()
        self.ignore_value_changes = False

    def set_studio_default(self):
        """Item's implementation to set current values as studio's overrides.

        Mark item and it's children as they have studio overrides.
        """
        raise NotImplementedError(
            "{} Method `set_studio_default` not implemented!".format(
                repr(self)
            )
        )

    def _reset_to_pype_default(self):
        self.ignore_value_changes = True
        self.reset_to_pype_default()
        self.ignore_value_changes = False

    def reset_to_pype_default(self):
        """Item's implementation to remove studio overrides.

        Mark item as it does not have studio overrides unset studio
        override values.
        """
        raise NotImplementedError(
            "{} Method `reset_to_pype_default` not implemented!".format(
                repr(self)
            )
        )

    def _remove_overrides(self):
        self.ignore_value_changes = True
        self.remove_overrides()
        self.ignore_value_changes = False

    def remove_overrides(self):
        """Item's implementation to remove project overrides.

        Mark item as does not have project overrides. Must not change
        `was_overriden` attribute value.
        """
        raise NotImplementedError(
            "{} Method `remove_overrides` not implemented!".format(
                repr(self)
            )
        )

    def _set_as_overriden(self):
        self.ignore_value_changes = True
        self.set_as_overriden()
        self.ignore_value_changes = False

    def set_as_overriden(self):
        """Item's implementation to set values as overriden for project.

        Mark item and all it's children as they're overriden. Must skip
        items with children items that has attributes `is_group`
        and `any_parent_is_group` set to False. In that case those items
        are not meant to be overridable and should trigger the method on it's
        children.

        """
        raise NotImplementedError(
            "{} Method `set_as_overriden` not implemented!".format(repr(self))
        )

    def hierarchical_style_update(self):
        """Trigger update style method down the hierarchy."""
        raise NotImplementedError(
            "{} Method `hierarchical_style_update` not implemented!".format(
                repr(self)
            )
        )

    def update_default_values(self, parent_values):
        """Fill default values on startup or on refresh.

        Default values stored in `pype` repository should update all items in
        schema. Each item should take values for his key and set it's value or
        pass values down to children items.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
        """
        raise NotImplementedError(
            "{} does not have implemented `update_default_values`".format(self)
        )

    def update_studio_values(self, parent_values):
        """Fill studio override values on startup or on refresh.

        Set studio value if is not set to NOT_SET, in that case studio
        overrides are not set yet.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
        """
        raise NotImplementedError(
            "{} does not have implemented `update_studio_values`".format(self)
        )

    def apply_overrides(self, parent_values):
        """Fill project override values on startup, refresh or project change.

        Set project value if is not set to NOT_SET, in that case project
        overrides are not set yet.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
        """
        raise NotImplementedError(
            "{} does not have implemented `apply_overrides`".format(self)
        )

    @property
    def child_has_studio_override(self):
        """Any children item has studio overrides."""
        raise NotImplementedError(
            "{} does not have implemented `child_has_studio_override`".format(
                self
            )
        )

    @property
    def child_modified(self):
        """Any children item is modified."""
        raise NotImplementedError(
            "{} does not have implemented `child_modified`".format(self)
        )

    @property
    def child_overriden(self):
        """Any children item has project overrides."""
        raise NotImplementedError(
            "{} does not have implemented `child_overriden`".format(self)
        )

    @property
    def child_invalid(self):
        """Any children item does not have valid value."""
        raise NotImplementedError(
            "{} does not have implemented `child_invalid`".format(self)
        )

    def get_invalid(self):
        """Return invalid item types all down the hierarchy."""
        raise NotImplementedError(
            "{} does not have implemented `get_invalid`".format(self)
        )

    def item_value(self):
        """Value of an item without key."""
        raise NotImplementedError(
            "Method `item_value` not implemented!"
        )


class InputObject(SettingObject):
    """Class for inputs with pre-implemented methods.

    Class is for item types not creating or using other item types, most
    of methods has same code in that case.
    """

    def update_default_values(self, parent_values):
        self._state = None
        self._is_modified = False

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if value is NOT_SET:
            if self.develop_mode:
                self.defaults_not_set = True
                value = self.default_input_value
                if value is NOT_SET:
                    raise NotImplementedError((
                        "{} Does not have implemented"
                        " attribute `default_input_value`"
                    ).format(self))

            else:
                raise ValueError(
                    "Default value is not set. This is implementation BUG."
                )
        else:
            self.defaults_not_set = False

        self.default_value = value
        self._has_studio_override = False
        self._had_studio_override = False
        self.set_value(value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._is_modified = False

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        self.studio_value = value
        if value is not NOT_SET:
            self._has_studio_override = True
            self._had_studio_override = True
            self.set_value(value)

        else:
            self._has_studio_override = False
            self._had_studio_override = False
            self.set_value(self.default_value)

    def apply_overrides(self, parent_values):
        self._is_modified = False
        self._state = None
        self._had_studio_override = bool(self._has_studio_override)
        if self._as_widget:
            override_value = parent_values
        elif parent_values is NOT_SET or self.key not in parent_values:
            override_value = NOT_SET
        else:
            override_value = parent_values[self.key]

        self.override_value = override_value

        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            if self.has_studio_override:
                value = self.studio_value
            else:
                value = self.default_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self.set_value(value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if not self.any_parent_as_widget:
            if self.is_overidable:
                self._is_overriden = True
            else:
                self._has_studio_override = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        elif self._has_studio_override:
            self._is_modified = self.item_value() != self.studio_value
        else:
            self._is_modified = self.item_value() != self.default_value

        self.update_style()

        self.value_changed.emit(self)

    def studio_overrides(self):
        if (
            not (self.as_widget or self.any_parent_as_widget)
            and not self.has_studio_override
        ):
            return NOT_SET, False
        return self.config_value(), self.is_group

    def overrides(self):
        if (
            not (self.as_widget or self.any_parent_as_widget)
            and not self.is_overriden
        ):
            return NOT_SET, False
        return self.config_value(), self.is_group

    def hierarchical_style_update(self):
        self.update_style()

    def _style_state(self):
        if self.as_widget:
            state = self.style_state(
                False,
                self._is_invalid,
                False,
                self._is_modified
            )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )
        return state

    def update_style(self):
        state = self._style_state()
        if self._state == state:
            return

        self._state = state

        self.input_field.setProperty("input-state", state)
        self.input_field.style().polish(self.input_field)
        if self.label_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        if self.has_studio_override:
            self.set_value(self.studio_value)
        else:
            self.set_value(self.default_value)
        self._is_overriden = False
        self._is_modified = False

    def reset_to_pype_default(self):
        self.set_value(self.default_value)
        self._has_studio_override = False

    def set_studio_default(self):
        self._has_studio_override = True

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._has_studio_override = self._had_studio_override
        if self.is_overidable:
            if self._was_overriden and self.override_value is not NOT_SET:
                self.set_value(self.override_value)
        else:
            if self._had_studio_override:
                self.set_value(self.studio_value)
            else:
                self.set_value(self.default_value)

        if not self.is_overidable:
            if self.has_studio_override:
                self._is_modified = self.studio_value != self.item_value()
            else:
                self._is_modified = self.default_value != self.item_value()
            self._is_overriden = False
            return

        self._is_modified = False
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        self._is_overriden = True

    @property
    def child_has_studio_override(self):
        return self._has_studio_override

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self._is_overriden

    @property
    def child_invalid(self):
        return self.is_invalid

    def get_invalid(self):
        output = []
        if self.is_invalid:
            output.append(self)
        return output

    def reset_children_attributes(self):
        return


class BooleanWidget(QtWidgets.QWidget, InputObject):
    default_input_value = True
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(BooleanWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not self.as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                layout.addWidget(label_widget, 0)
        self.label_widget = label_widget

        self.input_field = QtWidgets.QCheckBox(self)
        spacer = QtWidgets.QWidget(self)
        spacer.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        layout.addWidget(self.input_field, 0)
        layout.addWidget(spacer, 1)

        self.setFocusProxy(self.input_field)

        self.input_field.stateChanged.connect(self._on_value_change)

    def set_value(self, value):
        # Ignore value change because if `self.isChecked()` has same
        # value as `value` the `_on_value_change` is not triggered
        self.input_field.setChecked(value)

    def item_value(self):
        return self.input_field.isChecked()


class NumberWidget(QtWidgets.QWidget, InputObject):
    default_input_value = 0
    value_changed = QtCore.Signal(object)
    input_modifiers = ("minimum", "maximum", "decimal")

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(NumberWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        kwargs = {
            modifier: input_data.get(modifier)
            for modifier in self.input_modifiers
            if input_data.get(modifier)
        }
        self.input_field = NumberSpinBox(self, **kwargs)

        self.setFocusProxy(self.input_field)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0)
        self.label_widget = label_widget

        layout.addWidget(self.input_field, 1)

        self.input_field.valueChanged.connect(self._on_value_change)

    def set_value(self, value):
        self.input_field.setValue(value)

    def item_value(self):
        return self.input_field.value()


class TextWidget(QtWidgets.QWidget, InputObject):
    default_input_value = ""
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(TextWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        self.multiline = input_data.get("multiline", False)
        placeholder = input_data.get("placeholder")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if self.multiline:
            self.input_field = QtWidgets.QPlainTextEdit(self)
        else:
            self.input_field = QtWidgets.QLineEdit(self)

        if placeholder:
            self.input_field.setPlaceholderText(placeholder)

        self.setFocusProxy(self.input_field)

        layout_kwargs = {}
        if self.multiline:
            layout_kwargs["alignment"] = QtCore.Qt.AlignTop

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0, **layout_kwargs)
        self.label_widget = label_widget

        layout.addWidget(self.input_field, 1, **layout_kwargs)

        self.input_field.textChanged.connect(self._on_value_change)

    def set_value(self, value):
        if self.multiline:
            self.input_field.setPlainText(value)
        else:
            self.input_field.setText(value)

    def item_value(self):
        if self.multiline:
            return self.input_field.toPlainText()
        else:
            return self.input_field.text()


class PathInputWidget(QtWidgets.QWidget, InputObject):
    default_input_value = ""
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(PathInputWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0)
        self.label_widget = label_widget

        self.input_field = PathInput(self)
        self.setFocusProxy(self.input_field)
        layout.addWidget(self.input_field, 1)

        self.input_field.textChanged.connect(self._on_value_change)

    def set_value(self, value):
        self.input_field.setText(value)

    def focusOutEvent(self, event):
        self.input_field.clear_end_path()
        super(PathInput, self).focusOutEvent(event)

    def item_value(self):
        return self.input_field.text()


class EnumeratorWidget(QtWidgets.QWidget, InputObject):
    default_input_value = True
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(EnumeratorWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)
        self.multiselection = input_data.get("multiselection")
        self.enum_items = input_data["enum_items"]
        if not self.enum_items:
            raise ValueError("Attribute `enum_items` is not defined.")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                layout.addWidget(label_widget, 0)
        self.label_widget = label_widget

        if self.multiselection:
            placeholder = input_data.get("placeholder")
            self.input_field = MultiSelectionComboBox(
                placeholder=placeholder, parent=self
            )
        else:
            self.input_field = ComboBox(self)

        first_value = NOT_SET
        for enum_item in self.enum_items:
            for value, label in enum_item.items():
                if first_value is NOT_SET:
                    first_value = value
                self.input_field.addItem(label, value)
        self._first_value = first_value

        if self.multiselection:
            model = self.input_field.model()
            for idx in range(self.input_field.count()):
                model.item(idx).setCheckable(True)

        layout.addWidget(self.input_field, 0)

        self.setFocusProxy(self.input_field)

        self.input_field.value_changed.connect(self._on_value_change)

    @property
    def default_input_value(self):
        if self.multiselection:
            return []
        return self._first_value

    def set_value(self, value):
        # Ignore value change because if `self.isChecked()` has same
        # value as `value` the `_on_value_change` is not triggered
        self.input_field.set_value(value)

    def update_style(self):
        if self.as_widget:
            state = self.style_state(
                False,
                self._is_invalid,
                False,
                self._is_modified
            )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )

        if self._state == state:
            return

        self._state = state
        self.input_field.setProperty("input-state", state)
        self.input_field.style().polish(self.input_field)
        if self.label_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        return self.input_field.value()


class RawJsonInput(QtWidgets.QPlainTextEdit):
    tab_length = 4

    def __init__(self, *args, **kwargs):
        super(RawJsonInput, self).__init__(*args, **kwargs)
        self.setObjectName("RawJsonInput")
        self.setTabStopDistance(
            QtGui.QFontMetricsF(
                self.font()
            ).horizontalAdvance(" ") * self.tab_length
        )

    def sizeHint(self):
        document = self.document()
        layout = document.documentLayout()

        height = document.documentMargin() + 2 * self.frameWidth() + 1
        block = document.begin()
        while block != document.end():
            height += layout.blockBoundingRect(block).height()
            block = block.next()

        hint = super(RawJsonInput, self).sizeHint()
        hint.setHeight(height)

        return hint

    def set_value(self, value):
        if value is NOT_SET:
            value = ""
        elif not isinstance(value, str):
            try:
                value = json.dumps(value, indent=4)
            except Exception:
                value = ""
        self.setPlainText(value)

    def json_value(self):
        return json.loads(self.toPlainText())

    def has_invalid_value(self):
        try:
            self.json_value()
            return False
        except Exception:
            return True

    def resizeEvent(self, event):
        self.updateGeometry()
        super(RawJsonInput, self).resizeEvent(event)


class RawJsonWidget(QtWidgets.QWidget, InputObject):
    default_input_value = "{}"
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(RawJsonWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.input_field = RawJsonInput(self)
        self.input_field.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.setFocusProxy(self.input_field)

        if not self.as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0, alignment=QtCore.Qt.AlignTop)
        self.label_widget = label_widget

        layout.addWidget(self.input_field, 1, alignment=QtCore.Qt.AlignTop)

        self.input_field.textChanged.connect(self._on_value_change)

    def update_studio_values(self, parent_values):
        self._is_invalid = self.input_field.has_invalid_value()
        return super(RawJsonWidget, self).update_studio_values(parent_values)

    def set_value(self, value):
        self.input_field.set_value(value)

    def _on_value_change(self, *args, **kwargs):
        self._is_invalid = self.input_field.has_invalid_value()
        return super(RawJsonWidget, self)._on_value_change(*args, **kwargs)

    def item_value(self):
        if self.is_invalid:
            return NOT_SET
        return self.input_field.json_value()


class ListItem(QtWidgets.QWidget, SettingObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(
        self, item_schema, config_parent, parent, is_strict=False
    ):
        super(ListItem, self).__init__(parent)

        self._set_default_attributes()

        self._is_strict = is_strict

        self._parent = config_parent
        self._any_parent_is_group = True
        self._is_empty = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        char_up = qtawesome.charmap("fa.angle-up")
        char_down = qtawesome.charmap("fa.angle-down")

        if not self._is_strict:
            self.add_btn = QtWidgets.QPushButton("+")
            self.remove_btn = QtWidgets.QPushButton("-")
            self.up_btn = QtWidgets.QPushButton(char_up)
            self.down_btn = QtWidgets.QPushButton(char_down)

            font_up_down = qtawesome.font("fa", 13)
            self.up_btn.setFont(font_up_down)
            self.down_btn.setFont(font_up_down)

            self.add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.up_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.down_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

            self.add_btn.setFixedSize(self._btn_size, self._btn_size)
            self.remove_btn.setFixedSize(self._btn_size, self._btn_size)
            self.up_btn.setFixedSize(self._btn_size, self._btn_size)
            self.down_btn.setFixedSize(self._btn_size, self._btn_size)

            self.add_btn.setProperty("btn-type", "tool-item")
            self.remove_btn.setProperty("btn-type", "tool-item")
            self.up_btn.setProperty("btn-type", "tool-item")
            self.down_btn.setProperty("btn-type", "tool-item")

            self.add_btn.clicked.connect(self._on_add_clicked)
            self.remove_btn.clicked.connect(self._on_remove_clicked)
            self.up_btn.clicked.connect(self._on_up_clicked)
            self.down_btn.clicked.connect(self._on_down_clicked)

            layout.addWidget(self.add_btn, 0)
            layout.addWidget(self.remove_btn, 0)

        ItemKlass = TypeToKlass.types[item_schema["type"]]
        self.value_input = ItemKlass(
            item_schema,
            self,
            as_widget=True,
            label_widget=None
        )

        layout.addWidget(self.value_input, 1)

        if not self._is_strict:
            self.spacer_widget = QtWidgets.QWidget(self)
            self.spacer_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.spacer_widget.setVisible(False)

            layout.addWidget(self.spacer_widget, 1)

            layout.addWidget(self.up_btn, 0)
            layout.addWidget(self.down_btn, 0)

        self.value_input.value_changed.connect(self._on_value_change)

    @property
    def as_widget(self):
        return self._parent.as_widget

    @property
    def any_parent_as_widget(self):
        return self.as_widget or self._parent.any_parent_as_widget

    def set_as_empty(self, is_empty=True):
        self._is_empty = is_empty

        self.spacer_widget.setVisible(is_empty)
        self.value_input.setVisible(not is_empty)
        self.remove_btn.setEnabled(not is_empty)
        self.up_btn.setVisible(not is_empty)
        self.down_btn.setVisible(not is_empty)
        self.order_changed()
        self._on_value_change()

    def order_changed(self):
        row = self.row()
        parent_row_count = self.parent_rows_count()
        if parent_row_count == 1:
            self.up_btn.setVisible(False)
            self.down_btn.setVisible(False)
            return

        if not self.up_btn.isVisible():
            self.up_btn.setVisible(True)
            self.down_btn.setVisible(True)

        if row == 0:
            self.up_btn.setEnabled(False)
            self.down_btn.setEnabled(True)

        elif row == parent_row_count - 1:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(False)

        else:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(True)

    def _on_value_change(self, item=None):
        self.value_changed.emit(self)

    def row(self):
        return self._parent.input_fields.index(self)

    def parent_rows_count(self):
        return len(self._parent.input_fields)

    def _on_add_clicked(self):
        if self._is_empty:
            self.set_as_empty(False)
        else:
            self._parent.add_row(row=self.row() + 1)

    def _on_remove_clicked(self):
        self._parent.remove_row(self)

    def _on_up_clicked(self):
        row = self.row()
        self._parent.swap_rows(row - 1, row)

    def _on_down_clicked(self):
        row = self.row()
        self._parent.swap_rows(row, row + 1)

    def config_value(self):
        if not self._is_empty:
            return self.value_input.item_value()
        return NOT_SET

    @property
    def child_has_studio_override(self):
        return self.value_input.child_has_studio_override

    @property
    def child_modified(self):
        return self.value_input.child_modified

    @property
    def child_overriden(self):
        return self.value_input.child_overriden

    def hierarchical_style_update(self):
        self.value_input.hierarchical_style_update()

    def mouseReleaseEvent(self, event):
        return QtWidgets.QWidget.mouseReleaseEvent(self, event)

    def update_default_values(self, value):
        self.value_input.update_default_values(value)

    def update_studio_values(self, value):
        self.value_input.update_studio_values(value)

    def apply_overrides(self, value):
        self.value_input.apply_overrides(value)


class ListWidget(QtWidgets.QWidget, InputObject):
    default_input_value = []
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ListWidget, self).__init__(parent_widget)
        self.setObjectName("ListWidget")

        self.initial_attributes(input_data, parent, as_widget)

        object_type = input_data["object_type"]
        if isinstance(object_type, dict):
            self.item_schema = object_type
        else:
            self.item_schema = {
                "type": object_type
            }
            # Backwards compatibility
            input_modifiers = input_data.get("input_modifiers") or {}
            if input_modifiers:
                self.log.warning((
                    "Used deprecated key `input_modifiers` to define item."
                    " Rather use `object_type` as dictionary with modifiers."
                ))
                self.item_schema.update(input_modifiers)

        self.input_fields = []

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(5)

        if not self.as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label_widget = QtWidgets.QLabel(input_data["label"], self)
                layout.addWidget(label_widget, alignment=QtCore.Qt.AlignTop)

        self.label_widget = label_widget

        inputs_widget = QtWidgets.QWidget(self)
        inputs_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        layout.addWidget(inputs_widget)

        inputs_layout = QtWidgets.QVBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(3)

        self.inputs_widget = inputs_widget
        self.inputs_layout = inputs_layout

        self.add_row(is_empty=True)

    def count(self):
        return len(self.input_fields)

    def update_studio_values(self, parent_values):
        super(ListWidget, self).update_studio_values(parent_values)

        self.hierarchical_style_update()

    def set_value(self, value):
        previous_inputs = tuple(self.input_fields)
        for item_value in value:
            self.add_row(value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if self.count() == 0:
            self.add_row(is_empty=True)

    def swap_rows(self, row_1, row_2):
        if row_1 == row_2:
            return

        if row_1 > row_2:
            row_1, row_2 = row_2, row_1

        field_1 = self.input_fields[row_1]
        field_2 = self.input_fields[row_2]

        self.input_fields[row_1] = field_2
        self.input_fields[row_2] = field_1

        layout_index = self.inputs_layout.indexOf(field_1)
        self.inputs_layout.insertWidget(layout_index + 1, field_1)

        field_1.order_changed()
        field_2.order_changed()

    def add_row(self, row=None, value=None, is_empty=False):
        # Create new item
        item_widget = ListItem(self.item_schema, self, self.inputs_widget)

        previous_field = None
        next_field = None

        if row is None:
            if self.input_fields:
                previous_field = self.input_fields[-1]
            self.inputs_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            if row > 0:
                previous_field = self.input_fields[row - 1]

            max_index = self.count()
            if row < max_index:
                next_field = self.input_fields[row]

            self.inputs_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

        if previous_field:
            previous_field.order_changed()

        if next_field:
            next_field.order_changed()

        if is_empty:
            item_widget.set_as_empty()
        item_widget.value_changed.connect(self._on_value_change)

        item_widget.order_changed()

        previous_input = None
        for input_field in self.input_fields:
            if previous_input is not None:
                self.setTabOrder(
                    previous_input, input_field.value_input.focusProxy()
                )
            previous_input = input_field.value_input.focusProxy()

        # Set text if entered text is not None
        # else (when add button clicked) trigger `_on_value_change`
        if value is not None:
            if self._is_overriden:
                item_widget.apply_overrides(value)
            elif not self._has_studio_override:
                item_widget.update_default_values(value)
            else:
                item_widget.update_studio_values(value)
            self.hierarchical_style_update()
        else:
            self._on_value_change()
        self.updateGeometry()

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        row = self.input_fields.index(item_widget)
        previous_field = None
        next_field = None
        if row > 0:
            previous_field = self.input_fields[row - 1]

        if row != len(self.input_fields) - 1:
            next_field = self.input_fields[row + 1]

        self.inputs_layout.removeWidget(item_widget)
        self.input_fields.pop(row)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if previous_field:
            previous_field.order_changed()

        if next_field:
            next_field.order_changed()

        if self.count() == 0:
            self.add_row(is_empty=True)

        self._on_value_change()
        self.updateGeometry()

    def apply_overrides(self, parent_values):
        self._is_modified = False
        if parent_values is NOT_SET or self.key not in parent_values:
            override_value = NOT_SET
        else:
            override_value = parent_values[self.key]

        self.override_value = override_value

        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            if self.has_studio_override:
                value = self.studio_value
            else:
                value = self.default_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self._is_modified = False
        self._state = None

        self.set_value(value)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        if not self.label_widget:
            return

        state = self._style_state()
        if self._state == state:
            return

        self._state = state
        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        output = []
        for item in self.input_fields:
            value = item.config_value()
            if value is not NOT_SET:
                output.append(value)
        return output


class ListStrictWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)
    _default_input_value = None

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ListStrictWidget, self).__init__(parent_widget)
        self.setObjectName("ListStrictWidget")

        self.initial_attributes(input_data, parent, as_widget)

        self.input_fields = []

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(5)

        if not self.as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label_widget = QtWidgets.QLabel(input_data["label"], self)
                layout.addWidget(label_widget, alignment=QtCore.Qt.AlignTop)

        self.label_widget = label_widget

        self._add_children(layout, input_data)

    def _add_children(self, layout, input_data):
        inputs_widget = QtWidgets.QWidget(self)
        inputs_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        layout.addWidget(inputs_widget)

        horizontal = input_data.get("horizontal", True)
        if horizontal:
            inputs_layout = QtWidgets.QHBoxLayout(inputs_widget)
        else:
            inputs_layout = QtWidgets.QGridLayout(inputs_widget)

        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(3)

        self.inputs_widget = inputs_widget
        self.inputs_layout = inputs_layout

        children_item_mapping = []
        for child_configuration in input_data["object_types"]:
            item_widget = ListItem(
                child_configuration, self, self.inputs_widget, is_strict=True
            )

            self.input_fields.append(item_widget)
            item_widget.value_changed.connect(self._on_value_change)

            label = child_configuration.get("label")
            label_widget = None
            if label:
                label_widget = QtWidgets.QLabel(label, self)

            children_item_mapping.append((label_widget, item_widget))

        if horizontal:
            self._add_children_horizontally(children_item_mapping)
        else:
            self._add_children_vertically(children_item_mapping)

        self.updateGeometry()

    def _add_children_vertically(self, children_item_mapping):
        any_has_label = False
        for item_mapping in children_item_mapping:
            if item_mapping[0]:
                any_has_label = True
                break

        row = self.inputs_layout.count()
        if not any_has_label:
            self.inputs_layout.setColumnStretch(1, 1)
            for item_mapping in children_item_mapping:
                item_widget = item_mapping[1]
                self.inputs_layout.addWidget(item_widget, row, 0, 1, 1)

                spacer_widget = QtWidgets.QWidget(self.inputs_widget)
                self.inputs_layout.addWidget(spacer_widget, row, 1, 1, 1)
                row += 1

        else:
            self.inputs_layout.setColumnStretch(2, 1)
            for label_widget, item_widget in children_item_mapping:
                self.inputs_layout.addWidget(
                    label_widget, row, 0, 1, 1,
                    alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignTop
                )
                self.inputs_layout.addWidget(item_widget, row, 1, 1, 1)

                spacer_widget = QtWidgets.QWidget(self.inputs_widget)
                self.inputs_layout.addWidget(spacer_widget, row, 2, 1, 1)
                row += 1

    def _add_children_horizontally(self, children_item_mapping):
        for label_widget, item_widget in children_item_mapping:
            if label_widget:
                self.inputs_layout.addWidget(label_widget, 0)
            self.inputs_layout.addWidget(item_widget, 0)

        spacer_widget = QtWidgets.QWidget(self.inputs_widget)
        self.inputs_layout.addWidget(spacer_widget, 1)

    @property
    def default_input_value(self):
        if self._default_input_value is None:
            self.set_value(NOT_SET)
            self._default_input_value = self.item_value()
        return self._default_input_value

    def set_value(self, value):
        if self._is_overriden:
            method_name = "apply_overrides"
        elif not self._has_studio_override:
            method_name = "update_default_values"
        else:
            method_name = "update_studio_values"

        for idx, input_field in enumerate(self.input_fields):
            if value is NOT_SET:
                _value = value
            else:
                if idx > len(value) - 1:
                    _value = NOT_SET
                else:
                    _value = value[idx]
            _method = getattr(input_field, method_name)
            _method(_value)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        if not self.label_widget:
            return

        state = self._style_state()

        if self._state == state:
            return

        self._state = state
        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        output = []
        for item in self.input_fields:
            output.append(item.config_value())
        return output


class ModifiableDictItem(QtWidgets.QWidget, SettingObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(self, item_schema, config_parent, parent):
        super(ModifiableDictItem, self).__init__(parent)

        self._set_default_attributes()
        self._parent = config_parent

        any_parent_as_widget = config_parent.as_widget
        if not any_parent_as_widget:
            any_parent_as_widget = config_parent.any_parent_as_widget

        self._any_parent_as_widget = any_parent_as_widget
        self._any_parent_is_group = True

        self._is_empty = False
        self.is_key_duplicated = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        ItemKlass = TypeToKlass.types[item_schema["type"]]

        self.key_input = QtWidgets.QLineEdit(self)
        self.key_input.setObjectName("DictKey")

        self.value_input = ItemKlass(
            item_schema,
            self,
            as_widget=True,
            label_widget=None
        )
        self.add_btn = QtWidgets.QPushButton("+")
        self.remove_btn = QtWidgets.QPushButton("-")

        self.add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.add_btn.setProperty("btn-type", "tool-item")
        self.remove_btn.setProperty("btn-type", "tool-item")

        self.spacer_widget = QtWidgets.QWidget(self)
        self.spacer_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.spacer_widget.setVisible(False)

        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)
        layout.addWidget(self.key_input, 0)
        layout.addWidget(self.spacer_widget, 1)
        layout.addWidget(self.value_input, 1)

        self.setFocusProxy(self.value_input)

        self.add_btn.setFixedSize(self._btn_size, self._btn_size)
        self.remove_btn.setFixedSize(self._btn_size, self._btn_size)
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.remove_btn.clicked.connect(self.on_remove_clicked)

        self.key_input.textChanged.connect(self._on_value_change)
        self.value_input.value_changed.connect(self._on_value_change)

        self.origin_key = NOT_SET

    def key_value(self):
        return self.key_input.text()

    def is_key_invalid(self):
        if self._is_empty:
            return False

        if self.key_value() == "":
            return True

        if self.is_key_duplicated:
            return True
        return False

    def _on_value_change(self, item=None):
        self.update_style()
        self.value_changed.emit(self)

    def update_default_values(self, key, value):
        self.origin_key = key
        self.key_input.setText(key)
        self.value_input.update_default_values(value)

    def update_studio_values(self, key, value):
        self.origin_key = key
        self.key_input.setText(key)
        self.value_input.update_studio_values(value)

    def apply_overrides(self, key, value):
        self.origin_key = key
        self.key_input.setText(key)
        self.value_input.apply_overrides(value)

    @property
    def is_group(self):
        return self._parent.is_group

    def on_add_clicked(self):
        if self._is_empty:
            self.set_as_empty(False)
        else:
            self._parent.add_row(row=self.row() + 1)

    def on_remove_clicked(self):
        self._parent.remove_row(self)

    def set_as_empty(self, is_empty=True):
        self._is_empty = is_empty

        self.key_input.setVisible(not is_empty)
        self.value_input.setVisible(not is_empty)
        self.remove_btn.setEnabled(not is_empty)
        self.spacer_widget.setVisible(is_empty)
        self._on_value_change()

    @property
    def any_parent_is_group(self):
        return self._parent.any_parent_is_group

    def is_key_modified(self):
        return self.key_value() != self.origin_key

    def is_value_modified(self):
        return self.value_input.is_modified

    @property
    def is_modified(self):
        return self.is_value_modified() or self.is_key_modified()

    def hierarchical_style_update(self):
        self.value_input.hierarchical_style_update()
        self.update_style()

    @property
    def is_invalid(self):
        if self._is_empty:
            return False
        return self.is_key_invalid() or self.value_input.is_invalid

    def update_style(self):
        state = ""
        if not self._is_empty:
            if self.is_key_invalid():
                state = "invalid"
            elif self.is_key_modified():
                state = "modified"

        self.key_input.setProperty("state", state)
        self.key_input.style().polish(self.key_input)

    def row(self):
        return self._parent.input_fields.index(self)

    def item_value(self):
        key = self.key_input.text()
        value = self.value_input.item_value()
        return {key: value}

    def config_value(self):
        if self._is_empty:
            return {}
        return self.item_value()

    def mouseReleaseEvent(self, event):
        return QtWidgets.QWidget.mouseReleaseEvent(self, event)


class ModifiableDict(QtWidgets.QWidget, InputObject):
    default_input_value = {}
    # Should be used only for dictionary with one datatype as value
    # TODO this is actually input field (do not care if is group or not)
    value_changed = QtCore.Signal(object)
    expand_in_grid = True

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ModifiableDict, self).__init__(parent_widget)
        self.setObjectName("ModifiableDict")

        self.initial_attributes(input_data, parent, as_widget)

        self.input_fields = []

        self.key = input_data["key"]

        object_type = input_data["object_type"]
        if isinstance(object_type, dict):
            self.item_schema = object_type
        else:
            # Backwards compatibility
            self.item_schema = {
                "type": object_type
            }
            input_modifiers = input_data.get("input_modifiers") or {}
            if input_modifiers:
                self.log.warning((
                    "Used deprecated key `input_modifiers` to define item."
                    " Rather use `object_type` as dictionary with modifiers."
                ))
                self.item_schema.update(input_modifiers)

        if input_data.get("highlight_content", False):
            content_state = "hightlighted"
            bottom_margin = 5
        else:
            content_state = ""
            bottom_margin = 0

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        if as_widget:
            body_widget = None
            self.label_widget = label_widget
        else:
            body_widget = ExpandingWidget(input_data["label"], self)
            main_layout.addWidget(body_widget)

            self.body_widget = body_widget
            self.label_widget = body_widget.label_widget

            collapsable = input_data.get("collapsable", True)
            if collapsable:
                collapsed = input_data.get("collapsed", True)
                if not collapsed:
                    body_widget.toggle_content()

            else:
                body_widget.hide_toolbox(hide_content=False)

        if body_widget is None:
            content_parent_widget = self
        else:
            content_parent_widget = body_widget

        content_widget = QtWidgets.QWidget(content_parent_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", content_state)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 3, 0, bottom_margin)

        if body_widget is None:
            main_layout.addWidget(content_widget)
        else:
            body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.add_row(is_empty=True)

    def count(self):
        return len(self.input_fields)

    def set_value(self, value):
        previous_inputs = tuple(self.input_fields)
        for item_key, item_value in value.items():
            self.add_row(key=item_key, value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if self.count() == 0:
            self.add_row(is_empty=True)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        fields_by_keys = collections.defaultdict(list)
        for input_field in self.input_fields:
            key = input_field.key_value()
            fields_by_keys[key].append(input_field)

        for fields in fields_by_keys.values():
            if len(fields) == 1:
                field = fields[0]
                if field.is_key_duplicated:
                    field.is_key_duplicated = False
                    field.update_style()
            else:
                for field in fields:
                    field.is_key_duplicated = True
                    field.update_style()

        if self.is_overidable:
            self._is_overriden = True
        else:
            self._has_studio_override = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        elif self._has_studio_override:
            self._is_modified = self.item_value() != self.studio_value
        else:
            self._is_modified = self.item_value() != self.default_value

        self.update_style()

        self.value_changed.emit(self)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        state = self._style_state()

        if self._state == state:
            return

        self._state = state

        if self.label_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

        if not self.body_widget:
            return

        if state:
            child_state = "child-{}".format(state)
        else:
            child_state = ""

        self.body_widget.side_line_widget.setProperty("state", child_state)
        self.body_widget.side_line_widget.style().polish(
            self.body_widget.side_line_widget
        )

    def all_item_values(self):
        output = {}
        for item in self.input_fields:
            output.update(item.item_value())
        return output

    def item_value(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())
        return output

    def add_row(self, row=None, key=None, value=None, is_empty=False):
        # Create new item
        item_widget = ModifiableDictItem(
            self.item_schema, self, self.content_widget
        )
        if is_empty:
            item_widget.set_as_empty()

        item_widget.value_changed.connect(self._on_value_change)

        if row is None:
            self.content_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.content_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

        previous_input = None
        for input_field in self.input_fields:
            if previous_input is not None:
                self.setTabOrder(
                    previous_input, input_field.key_input
                )
            previous_input = input_field.value_input.focusProxy()
            self.setTabOrder(
                input_field.key_input, previous_input
            )

        # Set value if entered value is not None
        # else (when add button clicked) trigger `_on_value_change`
        if value is not None and key is not None:
            if not self._has_studio_override:
                item_widget.update_default_values(key, value)
            elif self._is_overriden:
                item_widget.apply_overrides(key, value)
            else:
                item_widget.update_studio_values(key, value)
            self.hierarchical_style_update()
        else:
            self._on_value_change()
        self.parent().updateGeometry()

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        self.content_layout.removeWidget(item_widget)
        self.input_fields.remove(item_widget)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if self.count() == 0:
            self.add_row(is_empty=True)

        self._on_value_change()
        self.parent().updateGeometry()

    @property
    def is_invalid(self):
        return self._is_invalid or self.child_invalid

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.is_invalid:
                return True
        return False


# Dictionaries
class DictWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)
    expand_in_grid = True

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(DictWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        self.input_fields = []

        self.checkbox_widget = None
        self.checkbox_key = input_data.get("checkbox_key")

        self.label_widget = label_widget

        if self.as_widget:
            self._ui_as_widget(input_data)
        else:
            self._ui_as_item(input_data)

    def _ui_as_item(self, input_data):
        self.key = input_data["key"]
        if input_data.get("highlight_content", False):
            content_state = "hightlighted"
            bottom_margin = 5
        else:
            content_state = ""
            bottom_margin = 0

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        body_widget = ExpandingWidget(input_data["label"], self)

        main_layout.addWidget(body_widget)

        content_widget = QtWidgets.QWidget(body_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", content_state)
        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, bottom_margin)

        body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        self.label_widget = body_widget.label_widget

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

        collapsable = input_data.get("collapsable", True)
        if len(self.input_fields) == 1 and self.checkbox_widget:
            body_widget.hide_toolbox(hide_content=True)

        elif collapsable:
            collapsed = input_data.get("collapsed", True)
            if not collapsed:
                body_widget.toggle_content()
        else:
            body_widget.hide_toolbox(hide_content=False)

    def _ui_as_widget(self, input_data):
        body = QtWidgets.QWidget(self)
        body.setObjectName("DictAsWidgetBody")
        show_borders = str(int(input_data.get("show_borders", True)))
        body.setProperty("show_borders", show_borders)

        content_layout = QtWidgets.QGridLayout(body)
        content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout = content_layout

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(body)

        for child_configuration in input_data["children"]:
            self.add_children_gui(child_configuration)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        row = self.content_layout.rowCount()
        if not getattr(klass, "is_input_type", False):
            item = klass(child_configuration, self)
            self.content_layout.addWidget(item, row, 0, 1, 2)
            return item

        if self.checkbox_key and not self.checkbox_widget:
            key = child_configuration.get("key")
            if key == self.checkbox_key:
                if child_configuration["type"] != "boolean":
                    self.log.warning((
                        "SCHEMA BUG: Dictionary item has set as checkbox"
                        " item invalid type \"{}\". Expected \"boolean\"."
                    ).format(child_configuration["type"]))
                else:
                    return self._add_checkbox_child(child_configuration)

        label_widget = None
        if not klass.expand_in_grid:
            label = child_configuration.get("label")
            if label is not None:
                label_widget = GridLabelWidget(label, self)
                self.content_layout.addWidget(label_widget, row, 0, 1, 1)

        item = klass(child_configuration, self, label_widget=label_widget)
        item.value_changed.connect(self._on_value_change)

        if label_widget:
            label_widget.input_field = item
            self.content_layout.addWidget(item, row, 1, 1, 1)
        else:
            self.content_layout.addWidget(item, row, 0, 1, 2)

        self.input_fields.append(item)
        return item

    def _add_checkbox_child(self, child_configuration):
        item = BooleanWidget(
            child_configuration, self, label_widget=self.label_widget
        )
        item.value_changed.connect(self._on_value_change)

        self.body_widget.add_widget_before_label(item)
        self.checkbox_widget = item
        self.input_fields.append(item)
        return item

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._is_modified = False

        for input_field in self.input_fields:
            input_field.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_default_values(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None

        value = NOT_SET
        if self.as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        for item in self.input_fields:
            item.update_default_values(value)

    def update_studio_values(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None
        value = NOT_SET
        if self.as_widget:
            value = parent_values
        else:
            if parent_values is not NOT_SET:
                value = parent_values.get(self.key, NOT_SET)

            self._has_studio_override = False
            if self.is_group and value is not NOT_SET:
                self._has_studio_override = True

            self._had_studio_override = bool(self._has_studio_override)

        for item in self.input_fields:
            item.update_studio_values(value)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None

        if self.as_widget:
            override_values = parent_values
        else:
            metadata = {}
            groups = tuple()
            override_values = NOT_SET
            if parent_values is not NOT_SET:
                metadata = parent_values.get(METADATA_KEY) or metadata
                groups = metadata.get("groups") or groups
                override_values = parent_values.get(self.key, override_values)

            self._is_overriden = self.key in groups

        for item in self.input_fields:
            item.apply_overrides(override_values)

        if not self.as_widget:
            if not self._is_overriden:
                self._is_overriden = (
                    self.is_group
                    and self.is_overidable
                    and self.child_overriden
                )
            self._was_overriden = bool(self._is_overriden)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group and not (self.as_widget or self.any_parent_as_widget):
            if self.is_overidable:
                self._is_overriden = True
            else:
                self._has_studio_override = True

            # TODO check if this is required
            self.hierarchical_style_update()

        self.value_changed.emit(self)

        self.update_style()

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self, is_overriden=None):
        # TODO add style update when used as widget
        if self.as_widget:
            return

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

        state = self.style_state(
            self.had_studio_override,
            child_invalid,
            self.is_overriden,
            self.is_modified
        )
        if self._state == state:
            return

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

        self._state = state

    @property
    def is_modified(self):
        if self.is_group:
            return self._is_modified or self.child_modified
        return False

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if (
                input_field.has_studio_override
                or input_field.child_has_studio_override
            ):
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
            if input_field.is_overriden or input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        output = []
        for input_field in self.input_fields:
            output.extend(input_field.get_invalid())
        return output

    def item_value(self):
        output = {}
        for input_field in self.input_fields:
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    def studio_overrides(self):
        if (
            not (self.as_widget or self.any_parent_as_widget)
            and not self.has_studio_override
            and not self.child_has_studio_override
        ):
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.studio_overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group


class DictInvisible(QtWidgets.QWidget, SettingObject):
    # TODO is not overridable by itself
    value_changed = QtCore.Signal(object)
    allow_actions = False
    expand_in_grid = True

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(DictInvisible, self).__init__(parent_widget)
        self.setObjectName("DictInvisible")

        self.initial_attributes(input_data, parent, as_widget)

        if self._is_group:
            raise TypeError("DictInvisible can't be marked as group input.")

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.content_layout = layout

        self.input_fields = []

        self.key = input_data["key"]

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        row = self.content_layout.rowCount()
        if not getattr(klass, "is_input_type", False):
            item = klass(child_configuration, self)
            self.content_layout.addWidget(item, row, 0, 1, 2)
            return item

        label_widget = None
        if not klass.expand_in_grid:
            label = child_configuration.get("label")
            if label is not None:
                label_widget = GridLabelWidget(label, self)
                self.content_layout.addWidget(label_widget, row, 0, 1, 1)

        item = klass(child_configuration, self, label_widget=label_widget)
        item.value_changed.connect(self._on_value_change)

        if label_widget:
            label_widget.input_field = item
            self.content_layout.addWidget(item, row, 1, 1, 1)
        else:
            self.content_layout.addWidget(item, row, 0, 1, 2)

        self.input_fields.append(item)
        return item

    def update_style(self, *args, **kwargs):
        return

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if (
                input_field.has_studio_override
                or input_field.child_has_studio_override
            ):
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
            if input_field.is_overriden or input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        output = []
        for input_field in self.input_fields:
            output.extend(input_field.get_invalid())
        return output

    def item_value(self):
        output = {}
        for input_field in self.input_fields:
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group and not self.any_parent_as_widget:
            if self.is_overidable:
                self._is_overriden = True
            else:
                self._has_studio_override = True
            self.hierarchical_style_update()

        self.value_changed.emit(self)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def discard_changes(self):
        self._is_modified = False
        self._is_overriden = self._was_overriden

        for input_field in self.input_fields:
            input_field.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_default_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        for item in self.input_fields:
            item.update_default_values(value)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        for item in self.input_fields:
            item.update_studio_values(value)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None

        metadata = {}
        groups = tuple()
        override_values = NOT_SET
        if parent_values is not NOT_SET:
            metadata = parent_values.get(METADATA_KEY) or metadata
            groups = metadata.get("groups") or groups
            override_values = parent_values.get(self.key, override_values)

        self._is_overriden = self.key in groups

        for item in self.input_fields:
            item.apply_overrides(override_values)

        if not self._is_overriden:
            self._is_overriden = (
                self.is_group
                and self.is_overidable
                and self.child_overriden
            )
        self._was_overriden = bool(self._is_overriden)

    def studio_overrides(self):
        if (
            not (self.as_widget or self.any_parent_as_widget)
            and not self.has_studio_override
            and not self.child_has_studio_override
        ):
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.studio_overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group


class PathWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)
    platforms = ("windows", "darwin", "linux")
    platform_labels_mapping = {
        "windows": "Windows",
        "darwin": "MacOS",
        "linux": "Linux"
    }

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(PathWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        # This is partial input and dictionary input
        if not self.any_parent_is_group and not self._as_widget:
            self._is_group = True
        else:
            self._is_group = False

        self.multiplatform = input_data.get("multiplatform", False)
        self.multipath = input_data.get("multipath", False)

        self.input_field = None

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not self.as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                layout.addWidget(label_widget, 0, alignment=QtCore.Qt.AlignTop)
        self.label_widget = label_widget

        self.content_widget = QtWidgets.QWidget(self)
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.content_widget)

        self.create_gui()

    @property
    def default_input_value(self):
        if self.multipath:
            value_type = list
        else:
            value_type = str

        if self.multiplatform:
            return {
                platform: value_type()
                for platform in self.platforms
            }
        return value_type()

    def create_gui(self):
        if not self.multiplatform and not self.multipath:
            input_data = {"key": self.key}
            path_input = PathInputWidget(
                input_data, self,
                as_widget=True, label_widget=self.label_widget
            )
            self.setFocusProxy(path_input)
            self.content_layout.addWidget(path_input)
            self.input_field = path_input
            path_input.value_changed.connect(self._on_value_change)
            return

        if not self.multiplatform:
            item_schema = {
                "key": self.key,
                "object_type": "path-input"
            }
            input_widget = ListWidget(
                item_schema, self,
                as_widget=True, label_widget=self.label_widget
            )
            self.setFocusProxy(input_widget)
            self.content_layout.addWidget(input_widget)
            self.input_field = input_widget
            input_widget.value_changed.connect(self._on_value_change)
            return

        item_schema = {
            "type": "dict",
            "show_borders": False,
            "children": []
        }
        for platform_key in self.platforms:
            platform_label = self.platform_labels_mapping[platform_key]
            child_item = {
                "key": platform_key,
                "label": platform_label
            }
            if self.multipath:
                child_item["type"] = "list"
                child_item["object_type"] = "path-input"
            else:
                child_item["type"] = "path-input"

            item_schema["children"].append(child_item)

        input_widget = DictWidget(
            item_schema, self, as_widget=True, label_widget=self.label_widget
        )
        self.content_layout.addWidget(input_widget)
        self.input_field = input_widget
        input_widget.value_changed.connect(self._on_value_change)

    def update_default_values(self, parent_values):
        self._state = None
        self._child_state = None
        self._is_modified = False

        value = NOT_SET
        if self.as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if value is NOT_SET:
            if self.develop_mode:
                self.defaults_not_set = True
                value = self.default_input_value
                if value is NOT_SET:
                    raise NotImplementedError((
                        "{} Does not have implemented"
                        " attribute `default_input_value`"
                    ).format(self))

            else:
                raise ValueError(
                    "Default value is not set. This is implementation BUG."
                )
        else:
            self.defaults_not_set = False

        self.default_value = value
        self._has_studio_override = False
        self._had_studio_override = False

        # TODO handle invalid value type
        self.input_field.update_default_values(value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._child_state = None
        self._is_modified = False

        value = NOT_SET
        if self.as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        self.studio_value = value
        if value is not NOT_SET:
            self._has_studio_override = True
            self._had_studio_override = True
        else:
            self._has_studio_override = False
            self._had_studio_override = False

        # TODO handle invalid value type
        self.input_field.update_studio_values(value)

    def apply_overrides(self, parent_values):
        self._is_modified = False
        self._state = None
        self._child_state = None

        override_values = NOT_SET
        if self._as_widget:
            override_values = parent_values
        elif parent_values is not NOT_SET:
            override_values = parent_values.get(self.key, NOT_SET)

        self._is_overriden = override_values is not NOT_SET
        self._was_overriden = bool(self._is_overriden)

        # TODO handle invalid value type
        self.input_field.update_studio_values(override_values)

        if not self._is_overriden:
            self._is_overriden = (
                self.is_group
                and self.is_overidable
                and self.child_overriden
            )
        self._is_modified = False
        self._was_overriden = bool(self._is_overriden)

    def set_value(self, value):
        if not self.multiplatform:
            return self.input_field.set_value(value)

        for _input_field in self.input_field.input_fields:
            _value = value.get(_input_field.key, NOT_SET)
            if _value is NOT_SET:
                continue
            _input_field.set_value(_value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if not self.any_parent_as_widget:
            if self.is_overidable:
                self._is_overriden = True
            else:
                self._has_studio_override = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        elif self._has_studio_override:
            self._is_modified = self.item_value() != self.studio_value
        else:
            self._is_modified = self.item_value() != self.default_value

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
            self.setProperty("state", child_state)
            self.style().polish(self)
            self._child_state = child_state

        if self.label_widget:
            state = self.style_state(
                child_has_studio_override,
                child_invalid,
                self.is_overriden,
                self.is_modified
            )
            if self._state == state:
                return

            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

            self._state = state

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        self.input_field.remove_overrides()

    def reset_to_pype_default(self):
        self.input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        self.input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._has_studio_override = self._had_studio_override

        self.input_field.discard_changes()

        if not self.is_overidable:
            if self.has_studio_override:
                self._is_modified = self.studio_value != self.item_value()
            else:
                self._is_modified = self.default_value != self.item_value()
            self._is_overriden = False
            return

        self._is_modified = False
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        self._is_overriden = True

    @property
    def child_has_studio_override(self):
        return self.has_studio_override

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def child_invalid(self):
        return self.input_field.child_invalid

    def hierarchical_style_update(self):
        self.input_field.hierarchical_style_update()
        self.update_style()

    def item_value(self):
        return self.input_field.item_value()

    def studio_overrides(self):
        if (
            not (self.as_widget or self.any_parent_as_widget)
            and not self.has_studio_override
            and not self.child_has_studio_override
        ):
            return NOT_SET, False

        value = {self.key: self.item_value()}
        return value, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        value = {self.key: self.item_value()}
        return value, self.is_group


# Proxy for form layout
class FormLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super(FormLabel, self).__init__(*args, **kwargs)
        self.item = None


class DictFormWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)
    allow_actions = False
    expand_in_grid = True

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(DictFormWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        self._as_widget = False
        self._is_group = False

        self.input_fields = []
        self.content_layout = QtWidgets.QFormLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        # Pop label to not be set in child
        label = child_configuration["label"]

        klass = TypeToKlass.types.get(item_type)

        label_widget = FormLabel(label, self)

        item = klass(child_configuration, self, label_widget=label_widget)
        label_widget.item = item

        item.value_changed.connect(self._on_value_change)
        self.content_layout.addRow(label_widget, item)
        self.input_fields.append(item)
        return item

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            position = self.mapFromGlobal(QtGui.QCursor().pos())
            widget = self.childAt(position)
            if widget and isinstance(widget, FormLabel):
                widget.item.mouseReleaseEvent(event)
                event.accept()
                return
        super(DictFormWidget, self).mouseReleaseEvent(event)

    def apply_overrides(self, parent_values):
        for item in self.input_fields:
            item.apply_overrides(parent_values)

    def discard_changes(self):
        self._is_modified = False
        self._is_overriden = self._was_overriden

        for item in self.input_fields:
            item.discard_changes()

        self._is_modified = self.child_modified

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_default_values(self, value):
        for item in self.input_fields:
            item.update_default_values(value)

    def update_studio_values(self, value):
        for item in self.input_fields:
            item.update_studio_values(value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self.value_changed.emit(self)
        if self.any_parent_is_group:
            self.hierarchical_style_update()

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if (
                input_field.has_studio_override
                or input_field.child_has_studio_override
            ):
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
            if input_field.is_overriden or input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        output = []
        for input_field in self.input_fields:
            output.extend(input_field.get_invalid())
        return output

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def item_value(self):
        output = {}
        for input_field in self.input_fields:
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    def config_value(self):
        return self.item_value()

    def studio_overrides(self):
        if (
            not (self.as_widget or self.any_parent_as_widget)
            and not self.has_studio_override
            and not self.child_has_studio_override
        ):
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.studio_overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return values, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return values, self.is_group


class LabelWidget(QtWidgets.QWidget):
    is_input_type = False

    def __init__(self, configuration, parent=None):
        super(LabelWidget, self).__init__(parent)
        self.setObjectName("LabelWidget")

        label = configuration["label"]

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        label_widget = QtWidgets.QLabel(label, self)
        layout.addWidget(label_widget)


class SplitterWidget(QtWidgets.QWidget):
    is_input_type = False
    _height = 2

    def __init__(self, configuration, parent=None):
        super(SplitterWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setObjectName("SplitterItem")
        splitter_item.setMinimumHeight(self._height)
        splitter_item.setMaximumHeight(self._height)
        layout.addWidget(splitter_item)


TypeToKlass.types["boolean"] = BooleanWidget
TypeToKlass.types["number"] = NumberWidget
TypeToKlass.types["text"] = TextWidget
TypeToKlass.types["path-input"] = PathInputWidget
TypeToKlass.types["raw-json"] = RawJsonWidget
TypeToKlass.types["list"] = ListWidget
TypeToKlass.types["list-strict"] = ListStrictWidget
TypeToKlass.types["enum"] = EnumeratorWidget
TypeToKlass.types["dict-modifiable"] = ModifiableDict
# DEPRECATED - remove when removed from schemas
TypeToKlass.types["dict-item"] = DictWidget
TypeToKlass.types["dict"] = DictWidget
TypeToKlass.types["dict-invisible"] = DictInvisible
TypeToKlass.types["path-widget"] = PathWidget
TypeToKlass.types["form"] = DictFormWidget

TypeToKlass.types["label"] = LabelWidget
TypeToKlass.types["splitter"] = SplitterWidget
