import json
import logging
from Qt import QtWidgets, QtCore, QtGui
from .widgets import (
    ExpandingWidget,
    ModifiedIntSpinBox,
    ModifiedFloatSpinBox
)
from .lib import NOT_SET, AS_WIDGET, METADATA_KEY, TypeToKlass


class ConfigObject:
    allow_actions = True

    default_state = ""

    _is_overriden = False
    _is_modified = False
    _was_overriden = False
    _is_invalid = False
    _is_group = False

    _log = None

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def is_modified(self):
        """Has object any changes that require saving."""
        return self._is_modified or (self.was_overriden != self.is_overriden)

    @property
    def is_overriden(self):
        """Is object overriden so should be saved to overrides."""
        return self._is_overriden or self._parent.is_overriden

    @property
    def was_overriden(self):
        """Initial state after applying overrides."""
        return self._was_overriden

    @property
    def is_invalid(self):
        """Value set in is not valid."""
        return self._is_invalid

    @property
    def is_group(self):
        """Value set in is not valid."""
        return self._is_group

    @property
    def is_overidable(self):
        """Should care about overrides."""
        return self._parent.is_overidable

    def any_parent_overriden(self):
        """Any of parent object up to top hiearchy is overriden."""
        if self._parent._is_overriden:
            return True
        return self._parent.any_parent_overriden()

    @property
    def ignore_value_changes(self):
        """Most of attribute changes are ignored on value change when True."""
        if not hasattr(self, "_parent"):
            raise NotImplementedError(
                "Object {} does not have `_parent` attribute".format(self)
            )
        return self._parent.ignore_value_changes

    @ignore_value_changes.setter
    def ignore_value_changes(self, value):
        """Setter for global parent item to apply changes for all inputs."""
        self._parent.ignore_value_changes = value

    @property
    def child_modified(self):
        """Any children item is modified."""
        raise NotImplementedError(
            "{} does not have implemented `child_modified`".format(self)
        )

    @property
    def child_overriden(self):
        """Any children item is overriden."""
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
        """Returns invalid items all down the hierarchy."""
        raise NotImplementedError(
            "{} does not have implemented `get_invalid`".format(self)
        )

    def item_value(self):
        """Value of an item without key."""
        raise NotImplementedError(
            "Method `item_value` not implemented!"
        )

    def config_value(self):
        """Output for saving changes or overrides."""
        return {self.key: self.item_value()}

    def value_from_values(self, values, keys=None):
        """Global getter of value based on loaded values."""
        if not values or values is AS_WIDGET:
            return NOT_SET

        if keys is None:
            keys = self.keys

        value = values
        for key in keys:
            if not isinstance(value, dict):
                raise TypeError(
                    "Expected dictionary got {}.".format(str(type(value)))
                )

            if key not in value:
                return NOT_SET
            value = value[key]
        return value

    def style_state(self, is_invalid, is_overriden, is_modified):
        items = []
        if is_invalid:
            items.append("invalid")
        else:
            if is_overriden:
                items.append("overriden")
            if is_modified:
                items.append("modified")
        return "-".join(items) or self.default_state

    def add_children_gui(self, child_configuration, values):
        raise NotImplementedError(
            "{} Method `add_children_gui` is not implemented!.".format(
                repr(self)
            )
        )

    def _discard_changes(self):
        self.ignore_value_changes = True
        self.discard_changes()
        self.ignore_value_changes = False

    def discard_changes(self):
        raise NotImplementedError(
            "{} Method `discard_changes` not implemented!".format(
                repr(self)
            )
        )

    def _remove_overrides(self):
        self.ignore_value_changes = True
        self.remove_overrides()
        self.ignore_value_changes = False

    def remove_overrides(self):
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
        raise NotImplementedError(
            "Method `set_as_overriden` not implemented!"
        )

    def hierarchical_style_update(self):
        raise NotImplementedError(
            "Method `hierarchical_style_update` not implemented!"
        )

    def mouseReleaseEvent(self, event):
        if self.allow_actions and event.button() == QtCore.Qt.RightButton:
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
                action = QtWidgets.QAction("Set as overriden")
                actions_mapping[action] = self._set_as_overriden
                menu.addAction(action)

            if (
                not self.any_parent_overriden()
                and (self.is_overriden or self.child_overriden)
            ):
                # TODO better label
                action = QtWidgets.QAction("Remove override")
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
            return

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


class InputObject(ConfigObject):
    def overrides(self):
        if not self.is_overriden:
            return NOT_SET, False
        return self.config_value(), self.is_group

    def hierarchical_style_update(self):
        self.update_style()

    def remove_overrides(self):
        self.set_value(self.start_value)
        self._is_overriden = False
        self._is_modified = False
        self._was_overriden = False

    def apply_overrides(self, parent_values):
        self._is_modified = False
        self._state = None

        if parent_values is NOT_SET or self.key not in parent_values:
            override_value = NOT_SET
        else:
            override_value = parent_values[self.key]

        self.override_value = override_value

        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            value = self.start_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self.set_value(value)

    def discard_changes(self):
        if (
            self.is_overidable
            and self.override_value is not NOT_SET
            and self._was_overriden is True
        ):
            self.set_value(self.override_value)
        else:
            self.set_value(self.start_value)

        if not self.is_overidable:
            self._is_modified = self.global_value != self.item_value()
            self._is_overriden = False
            return

        self._is_modified = False
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        self._is_overriden = True

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
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self._is_group = input_data.get("is_group", False)
        self.default_value = input_data.get("default", NOT_SET)

        self._state = None

        super(BooleanWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.checkbox = QtWidgets.QCheckBox(self)

        self.setFocusProxy(self.checkbox)

        self.checkbox.setAttribute(QtCore.Qt.WA_StyledBackground)
        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            label_widget.setAttribute(QtCore.Qt.WA_StyledBackground)
            layout.addWidget(label_widget, 0)

        layout.addWidget(self.checkbox, 1)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

        self.update_global_values(values)
        self.override_value = NOT_SET

        self.checkbox.stateChanged.connect(self._on_value_change)

    def update_global_values(self, values):
        value = NOT_SET
        if not self._as_widget:
            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.checkbox.setChecked(value)

            elif self.default_value is not NOT_SET:
                self.checkbox.setChecked(self.default_value)

        self.global_value = value
        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        # Ignore value change because if `self.isChecked()` has same
        # value as `value` the `_on_value_change` is not triggered
        self.checkbox.setChecked(value)

        if global_value:
            self.global_value = self.item_value()

        self._on_value_change()

    def clear_value(self):
        self.set_value(False)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        _value = self.item_value()
        is_modified = None
        if self.is_overidable:
            self._is_overriden = True
            if self.override_value is not None:
                is_modified = _value != self.override_value

        if is_modified is None:
            is_modified = _value != self.global_value

        self._is_modified = is_modified

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
        else:
            property_name = "state"

        self.label_widget.setProperty(property_name, state)
        self.label_widget.style().polish(self.label_widget)
        self._state = state

    def item_value(self):
        return self.checkbox.isChecked()


class IntegerWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)
    input_modifiers = ("minimum", "maximum")

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self._is_group = input_data.get("is_group", False)
        self.default_value = input_data.get("default", NOT_SET)

        self._state = None

        super(IntegerWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        kwargs = {
            modifier: input_data.get(modifier)
            for modifier in self.input_modifiers
            if input_data.get(modifier)
        }
        self.int_input = ModifiedIntSpinBox(self, **kwargs)

        self.setFocusProxy(self.int_input)

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.int_input, 1)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

        self.update_global_values(values)

        self.override_value = NOT_SET

        self.int_input.valueChanged.connect(self._on_value_change)

    def update_global_values(self, values):
        value = NOT_SET
        if not self._as_widget:
            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.int_input.setValue(value)

            elif self.default_value is not NOT_SET:
                self.int_input.setValue(self.default_value)

        self.global_value = value
        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        self.int_input.setValue(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def clear_value(self):
        self.set_value(0)

    def reset_value(self):
        self.set_value(self.start_value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self._is_modified = self.item_value() != self.global_value
        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.int_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.int_input.value()


class FloatWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)
    input_modifiers = ("minimum", "maximum", "decimal")

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self._is_group = input_data.get("is_group", False)
        self.default_value = input_data.get("default", NOT_SET)

        self._state = None

        super(FloatWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        kwargs = {
            modifier: input_data.get(modifier)
            for modifier in self.input_modifiers
            if input_data.get(modifier)
        }
        self.float_input = ModifiedFloatSpinBox(self, **kwargs)

        self.setFocusProxy(self.float_input)

        decimals = input_data.get("decimals", 5)
        maximum = input_data.get("maximum")
        minimum = input_data.get("minimum")

        self.float_input.setDecimals(decimals)
        if maximum is not None:
            self.float_input.setMaximum(float(maximum))
        if minimum is not None:
            self.float_input.setMinimum(float(minimum))

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.float_input, 1)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

        self.update_global_values(values)

        self.override_value = NOT_SET

        self.float_input.valueChanged.connect(self._on_value_change)

    def update_global_values(self, values):
        value = NOT_SET
        if not self._as_widget:
            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.float_input.setValue(value)

            elif self.default_value is not NOT_SET:
                self.float_input.setValue(self.default_value)

        self.global_value = value
        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        self.float_input.setValue(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.global_value)

    def clear_value(self):
        self.set_value(0)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self._is_modified = self.item_value() != self.global_value
        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.float_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.float_input.value()


class TextSingleLineWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self._is_group = input_data.get("is_group", False)
        self.default_value = input_data.get("default", NOT_SET)

        self._state = None

        super(TextSingleLineWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.text_input = QtWidgets.QLineEdit(self)

        self.setFocusProxy(self.text_input)

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.text_input, 1)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

        self.update_global_values(values)

        self.override_value = NOT_SET

        self.text_input.textChanged.connect(self._on_value_change)

    def update_global_values(self, values):
        value = NOT_SET
        if not self._as_widget:
            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.text_input.setText(value)

            elif self.default_value is not NOT_SET:
                self.text_input.setText(self.default_value)

        self.global_value = value
        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        self.text_input.setText(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value("")

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self._is_modified = self.item_value() != self.global_value
        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.text_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.text_input.text()


class TextMultiLineWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self._is_group = input_data.get("is_group", False)
        self.default_value = input_data.get("default", NOT_SET)

        self._state = None

        super(TextMultiLineWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.text_input = QtWidgets.QPlainTextEdit(self)

        self.setFocusProxy(self.text_input)

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.text_input, 1)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

        self.update_global_values(values)

        self.override_value = NOT_SET

        self.text_input.textChanged.connect(self._on_value_change)

    def update_global_values(self, values):
        value = NOT_SET
        if not self._as_widget:
            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.text_input.setPlainText(value)

            elif self.default_value is not NOT_SET:
                self.text_input.setPlainText(self.default_value)

        self.global_value = value
        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        self.text_input.setPlainText(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value("")

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self._is_modified = self.item_value() != self.global_value
        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.text_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.text_input.toPlainText()


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

    def set_value(self, value, *, global_value=False):
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
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self._is_group = input_data.get("is_group", False)
        self.default_value = input_data.get("default", NOT_SET)

        self._state = None

        super(RawJsonWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text_input = RawJsonInput(self)
        self.text_input.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.setFocusProxy(self.text_input)

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.text_input, 1)

        self.override_value = NOT_SET

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

        self.update_global_values(values)

        self.text_input.textChanged.connect(self._on_value_change)

    def update_global_values(self, values):
        value = NOT_SET
        if not self._as_widget:
            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.text_input.set_value(value)

            elif self.default_value is not NOT_SET:
                self.text_input.set_value(self.default_value)

            self._is_invalid = self.text_input.has_invalid_value()

        self.global_value = value
        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        self.text_input.set_value(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value("")

    def _on_value_change(self, item=None):
        self._is_invalid = self.text_input.has_invalid_value()
        if self.ignore_value_changes:
            return

        self._is_invalid = self.text_input.has_invalid_value()
        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.global_value

        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.text_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        if self.is_invalid:
            return NOT_SET
        return self.text_input.json_value()


class ListItem(QtWidgets.QWidget, ConfigObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(self, object_type, input_modifiers, config_parent, parent):
        self._parent = config_parent

        super(ListItem, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.add_btn = QtWidgets.QPushButton("+")
        self.remove_btn = QtWidgets.QPushButton("-")

        self.add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.add_btn.setFixedSize(self._btn_size, self._btn_size)
        self.remove_btn.setFixedSize(self._btn_size, self._btn_size)

        self.add_btn.setProperty("btn-type", "tool-item")
        self.remove_btn.setProperty("btn-type", "tool-item")

        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)

        self.add_btn.clicked.connect(self.on_add_clicked)
        self.remove_btn.clicked.connect(self.on_remove_clicked)

        ItemKlass = TypeToKlass.types[object_type]
        self.value_input = ItemKlass(
            input_modifiers,
            AS_WIDGET,
            [],
            self,
            None
        )
        layout.addWidget(self.value_input, 1)

        self.value_input.value_changed.connect(self._on_value_change)

    def set_as_empty(self, is_empty=True):
        self.value_input.setEnabled(not is_empty)
        self.remove_btn.setEnabled(not is_empty)
        self._on_value_change()

    def _on_value_change(self, item=None):
        self.value_changed.emit(self)

    def row(self):
        return self._parent.input_fields.index(self)

    def on_add_clicked(self):
        if self.value_input.isEnabled():
            self._parent.add_row(row=self.row() + 1)
        else:
            self.set_as_empty(False)

    def on_remove_clicked(self):
        self._parent.remove_row(self)

    def config_value(self):
        if self.value_input.isEnabled():
            return self.value_input.item_value()
        return NOT_SET


class ListWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        super(ListWidget, self).__init__(parent)
        self.setObjectName("ListWidget")

        self._state = None
        self._is_group = input_data.get("is_group", False)

        self.object_type = input_data["object_type"]
        self.default_value = input_data.get("default", NOT_SET)
        self.input_modifiers = input_data.get("input_modifiers") or {}

        self.input_fields = []

        inputs_widget = QtWidgets.QWidget(self)
        inputs_widget.setAttribute(QtCore.Qt.WA_StyledBackground)

        inputs_layout = QtWidgets.QVBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 5, 0, 5)
        inputs_layout.setSpacing(3)

        self.inputs_widget = inputs_widget
        self.inputs_layout = inputs_layout

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget)

        self.label_widget = label_widget

        layout.addWidget(inputs_widget)

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        self.update_global_values(values)

        self.override_value = NOT_SET

    def count(self):
        return len(self.input_fields)

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value([])

    def update_global_values(self, values):
        old_inputs = tuple(self.input_fields)

        value = self.value_from_values(values)

        self.global_value = value

        if value is not NOT_SET:
            for item_value in value:
                self.add_row(value=item_value)

        elif self.default_value is not NOT_SET:
            for item_value in self.default_value:
                self.add_row(value=item_value)

        for old_input in old_inputs:
            self.remove_row(old_input)

        if self.count() == 0:
            self.add_row(is_empty=True)

        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        previous_inputs = tuple(self.input_fields)
        for item_value in value:
            self.add_row(value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if global_value:
            self.global_value = value
            self.start_value = self.item_value()
            self._on_value_change()

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return
        self._is_modified = self.item_value() != self.global_value
        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def add_row(self, row=None, value=None, is_empty=False):
        # Create new item
        item_widget = ListItem(
            self.object_type, self.input_modifiers, self, self.inputs_widget
        )
        if is_empty:
            item_widget.set_as_empty()
        item_widget.value_changed.connect(self._on_value_change)

        if row is None:
            self.inputs_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.inputs_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

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
            item_widget.value_input.set_value(value, global_value=True)
        else:
            self._on_value_change()
        self.updateGeometry()

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        self.inputs_layout.removeWidget(item_widget)
        self.input_fields.remove(item_widget)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if self.count() == 0:
            self.add_row(is_empty=True)

        self._on_value_change()
        self.updateGeometry()

    def apply_overrides(self, parent_values):
        if parent_values is NOT_SET or self.key not in parent_values:
            override_value = NOT_SET
        else:
            override_value = parent_values[self.key]

        self.override_value = override_value

        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            value = self.start_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self._is_modified = False
        self._state = None

        self.set_value(value)

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        output = []
        for item in self.input_fields:
            value = item.config_value()
            if value is not NOT_SET:
                output.append(value)
        return output


class ModifiableDictItem(QtWidgets.QWidget, ConfigObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(self, object_type, input_modifiers, config_parent, parent):
        self._parent = config_parent

        super(ModifiableDictItem, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        ItemKlass = TypeToKlass.types[object_type]

        self.key_input = QtWidgets.QLineEdit(self)
        self.key_input.setObjectName("DictKey")

        self.value_input = ItemKlass(
            input_modifiers,
            AS_WIDGET,
            [],
            self,
            None
        )
        self.add_btn = QtWidgets.QPushButton("+")
        self.remove_btn = QtWidgets.QPushButton("-")

        self.add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.add_btn.setProperty("btn-type", "tool-item")
        self.remove_btn.setProperty("btn-type", "tool-item")

        layout.addWidget(self.key_input, 0)
        layout.addWidget(self.value_input, 1)
        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)

        self.setFocusProxy(self.value_input)

        self.add_btn.setFixedSize(self._btn_size, self._btn_size)
        self.remove_btn.setFixedSize(self._btn_size, self._btn_size)
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.remove_btn.clicked.connect(self.on_remove_clicked)

        self.key_input.textChanged.connect(self._on_value_change)
        self.value_input.value_changed.connect(self._on_value_change)

        # TODO This doesn't make sence!
        self.default_key = self._key()
        self.global_value = self.value_input.item_value()

        self.override_key = NOT_SET
        self.override_value = NOT_SET

        self.is_single = False

    def _key(self):
        return self.key_input.text()

    def _on_value_change(self, item=None):
        self.update_style()
        self.value_changed.emit(self)

    @property
    def is_group(self):
        return self._parent.is_group

    @property
    def any_parent_is_group(self):
        return self._parent.any_parent_is_group

    def is_key_modified(self):
        return self._key() != self.default_key

    def is_value_modified(self):
        return self.value_input.is_modified

    @property
    def is_modified(self):
        return self.is_value_modified() or self.is_key_modified()

    def update_style(self):
        if self.is_key_modified():
            state = "modified"
        else:
            state = ""

        self.key_input.setProperty("state", state)
        self.key_input.style().polish(self.key_input)

    def row(self):
        return self._parent.input_fields.index(self)

    def on_add_clicked(self):
        self._parent.add_row(row=self.row() + 1)

    def on_remove_clicked(self):
        if self.is_single:
            self.value_input.clear_value()
            self.key_input.setText("")
        else:
            self._parent.remove_row(self)

    def config_value(self):
        key = self.key_input.text()
        value = self.value_input.item_value()
        if not key:
            return {}
        return {key: value}


class ModifiableDict(ExpandingWidget, InputObject):
    # Should be used only for dictionary with one datatype as value
    # TODO this is actually input field (do not care if is group or not)
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent,
        label_widget=None
    ):
        self._parent = parent

        super(ModifiableDict, self).__init__(input_data["label"], parent)
        self.setObjectName("ModifiableDict")

        self._state = None

        self.input_fields = []

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self._is_group = input_data.get("is_group", False)

        inputs_widget = QtWidgets.QWidget(self)
        inputs_widget.setAttribute(QtCore.Qt.WA_StyledBackground)

        inputs_layout = QtWidgets.QVBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(5, 5, 0, 5)
        inputs_layout.setSpacing(5)

        self.set_content_widget(inputs_widget)

        self.inputs_widget = inputs_widget
        self.inputs_layout = inputs_layout

        self.object_type = input_data["object_type"]
        self.default_value = input_data.get("default", NOT_SET)
        self.input_modifiers = input_data.get("input_modifiers") or {}

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        self.override_value = NOT_SET

        self.update_global_values(values)

    def count(self):
        return len(self.input_fields)

    def update_global_values(self, values):
        old_inputs = tuple(self.input_fields)

        value = self.value_from_values(values)

        self.global_value = value

        if value is not NOT_SET:
            for item_key, item_value in value.items():
                self.add_row(key=item_key, value=item_value)

        elif self.default_value is not NOT_SET:
            for item_key, item_value in self.default_value.items():
                self.add_row(key=item_key, value=item_value)

        if self.count() == 0:
            self.add_row()

        for old_input in old_inputs:
            self.remove_row(old_input)

        self.start_value = self.item_value()

        self._is_modified = self.global_value != self.start_value

    def set_value(self, value, *, global_value=False):
        previous_inputs = tuple(self.input_fields)
        for item_key, item_value in value.items():
            self.add_row(key=item_key, value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if global_value:
            self.global_value = value
            self.start_value = self.item_value()
            self._on_value_change()

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self.is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.global_value

        self.value_changed.emit(self)

        self.update_style()

    def update_style(self):
        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        if state:
            child_state = "child-{}".format(state)
        else:
            child_state = ""

        self.setProperty("state", child_state)
        self.style().polish(self)

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

        self._state = state

    def item_value(self):
        output = {}
        for item in self.input_fields:
            item_value = item.config_value()
            if item_value:
                output.update(item_value)
        return output

    def add_row(self, row=None, key=None, value=None):
        # Create new item
        item_widget = ModifiableDictItem(
            self.object_type, self.input_modifiers, self, self.inputs_widget
        )

        # Set/unset if new item is single item
        current_count = self.count()
        if current_count == 0:
            item_widget.is_single = True
        elif current_count == 1:
            for _input_field in self.input_fields:
                _input_field.is_single = False

        item_widget.value_changed.connect(self._on_value_change)

        if row is None:
            self.inputs_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.inputs_layout.insertWidget(row, item_widget)
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
            item_widget.default_key = key
            item_widget.key_input.setText(key)
            item_widget.value_input.set_value(value, global_value=True)
        else:
            self._on_value_change()
        self.parent().updateGeometry()

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        self.inputs_layout.removeWidget(item_widget)
        self.input_fields.remove(item_widget)
        item_widget.setParent(None)
        item_widget.deleteLater()

        current_count = self.count()
        if current_count == 0:
            self.add_row()
        elif current_count == 1:
            for _input_field in self.input_fields:
                _input_field.is_single = True

        self._on_value_change()
        self.parent().updateGeometry()


# Dictionaries
class DictExpandWidget(ExpandingWidget, ConfigObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        if values is AS_WIDGET:
            raise TypeError("Can't use \"{}\" as widget item.".format(
                self.__class__.__name__
            ))
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self._is_group = input_data.get("is_group", False)

        self._state = None
        self._child_state = None

        super(DictExpandWidget, self).__init__(input_data["label"], parent)

        content_widget = QtWidgets.QWidget(self)
        content_widget.setVisible(False)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 0, 3)

        self.set_content_widget(content_widget)

        expanded = input_data.get("expanded", False)
        if expanded:
            self.toggle_content()

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        self.content_widget = content_widget
        self.content_layout = content_layout

        self.input_fields = []

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data, values)

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        self._was_overriden = False
        for item in self.input_fields:
            item.remove_overrides()

    def discard_changes(self):
        for item in self.input_fields:
            item.discard_changes()

        self._is_modified = self.child_modified
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_global_values(self, values):
        for item in self.input_fields:
            item.update_global_values(values)

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

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group:
            if self.is_overidable:
                self._is_overriden = True

            # TODO update items
            if item is not None:
                for _item in self.input_fields:
                    if _item is not item:
                        _item.update_style()

        self.value_changed.emit(self)

        self.update_style()

    def hierarchical_style_update(self):
        self.update_style()
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def update_style(self, is_overriden=None):
        child_modified = self.child_modified
        child_state = self.style_state(
            self.child_invalid, self.child_overriden, child_modified
        )
        if child_state:
            child_state = "child-{}".format(child_state)

        if child_state != self._child_state:
            self.setProperty("state", child_state)
            self.style().polish(self)
            self._child_state = child_state

        state = self.style_state(
            self.is_invalid, self.is_overriden, self.is_modified
        )
        if self._state == state:
            return

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

        self._state = state

    @property
    def is_modified(self):
        if self.is_group:
            return self.child_modified
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

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        item = klass(
            child_configuration, values, self.keys, self
        )
        item.value_changed.connect(self._on_value_change)
        self.content_layout.addWidget(item)

        self.input_fields.append(item)
        return item

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


class DictWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        if values is AS_WIDGET:
            raise TypeError("Can't use \"{}\" as widget item.".format(
                self.__class__.__name__
            ))
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self._is_group = input_data.get("is_group", False)

        self._state = None
        self._child_state = None

        super(DictWidget, self).__init__(parent)
        self.setObjectName("DictWidget")

        body_widget = QtWidgets.QWidget(self)

        label_widget = QtWidgets.QLabel(
            input_data["label"], parent=body_widget
        )
        label_widget.setObjectName("DictLabel")

        content_widget = QtWidgets.QWidget(body_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 0, 3)

        body_layout = QtWidgets.QVBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(5)
        body_layout.addWidget(label_widget)
        body_layout.addWidget(content_widget)

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 0, 5)
        main_layout.setSpacing(0)
        main_layout.addWidget(body_widget)

        self.label_widget = label_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        self.input_fields = []

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data, values)

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        self._was_overriden = False
        for item in self.input_fields:
            item.remove_overrides()

    def discard_changes(self):
        for item in self.input_fields:
            item.discard_changes()

        self._is_modified = self.child_modified
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_global_values(self, values):
        for item in self.input_fields:
            item.update_global_values(values)

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

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group:
            if self.is_overidable:
                self._is_overriden = True

            # TODO update items
            if item is not None:
                for _item in self.input_fields:
                    if _item is not item:
                        _item.update_style()

        self.value_changed.emit(self)

        self.update_style()

    def hierarchical_style_update(self):
        self.update_style()
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def update_style(self, is_overriden=None):
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

    @property
    def is_modified(self):
        if self.is_group:
            return self.child_modified
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

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        item = klass(
            child_configuration, values, self.keys, self
        )
        item.value_changed.connect(self._on_value_change)
        self.content_layout.addWidget(item)

        self.input_fields.append(item)
        return item

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


class DictInvisible(QtWidgets.QWidget, ConfigObject):
    # TODO is not overridable by itself
    value_changed = QtCore.Signal(object)
    allow_actions = False

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group
        self._is_group = input_data.get("is_group", False)

        super(DictInvisible, self).__init__(parent)
        self.setObjectName("DictInvisible")

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.input_fields = []

        self.key = input_data["key"]
        self.keys = list(parent_keys)
        self.keys.append(self.key)

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data, values)

    def update_style(self, *args, **kwargs):
        return

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

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        item = klass(
            child_configuration, values, self.keys, self
        )
        self.layout().addWidget(item)

        item.value_changed.connect(self._on_value_change)

        self.input_fields.append(item)
        return item

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group:
            if self.is_overidable:
                self._is_overriden = True
            # TODO update items
            if item is not None:
                is_overriden = self.is_overriden
                for _item in self.input_fields:
                    if _item is not item:
                        _item.update_style(is_overriden)

        self.value_changed.emit(self)

    def hierarchical_style_update(self):
        self.update_style()
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        self._was_overriden = False
        for item in self.input_fields:
            item.remove_overrides()

    def discard_changes(self):
        for item in self.input_fields:
            item.discard_changes()

        self._is_modified = self.child_modified
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_global_values(self, values):
        for item in self.input_fields:
            item.update_global_values(values)

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


class FormLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super(FormLabel, self).__init__(*args, **kwargs)
        self.item = None


# Proxy for form layout
class DictFormWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)
    allow_actions = False

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self._is_group = False

        super(DictFormWidget, self).__init__(parent)

        self.input_fields = {}
        self.content_layout = QtWidgets.QFormLayout(self)

        self.keys = list(parent_keys)

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data, values)

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
        for item in self.input_fields.values():
            item.apply_overrides(parent_values)

    def discard_changes(self):
        for item in self.input_fields.values():
            item.discard_changes()

        self._is_modified = self.child_modified
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_global_values(self, values):
        for item in self.input_fields.values():
            item.update_global_values(values)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return
        self.value_changed.emit(self)

    @property
    def child_modified(self):
        for input_field in self.input_fields.values():
            if input_field.child_modified:
                return True
        return False

    @property
    def child_overriden(self):
        for input_field in self.input_fields.values():
            if input_field.is_overriden or input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields.values():
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        output = []
        for input_field in self.input_fields.values():
            output.extend(input_field.get_invalid())
        return output

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        key = child_configuration["key"]
        # Pop label to not be set in child
        label = child_configuration["label"]

        klass = TypeToKlass.types.get(item_type)

        label_widget = FormLabel(label, self)

        item = klass(
            child_configuration, values, self.keys, self, label_widget
        )
        label_widget.item = item

        item.value_changed.connect(self._on_value_change)
        self.content_layout.addRow(label_widget, item)
        self.input_fields[key] = item
        return item

    def hierarchical_style_update(self):
        for input_field in self.input_fields.values():
            input_field.hierarchical_style_update()

    def item_value(self):
        output = {}
        for input_field in self.input_fields.values():
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    def config_value(self):
        return self.item_value()

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


TypeToKlass.types["boolean"] = BooleanWidget
TypeToKlass.types["text-singleline"] = TextSingleLineWidget
TypeToKlass.types["text-multiline"] = TextMultiLineWidget
TypeToKlass.types["raw-json"] = RawJsonWidget
TypeToKlass.types["int"] = IntegerWidget
TypeToKlass.types["float"] = FloatWidget
TypeToKlass.types["dict-modifiable"] = ModifiableDict
TypeToKlass.types["dict"] = DictWidget
TypeToKlass.types["dict-expanding"] = DictExpandWidget
TypeToKlass.types["dict-form"] = DictFormWidget
TypeToKlass.types["dict-invisible"] = DictInvisible
TypeToKlass.types["list"] = ListWidget
