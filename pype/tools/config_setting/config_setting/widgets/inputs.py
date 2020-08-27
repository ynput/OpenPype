import json
from Qt import QtWidgets, QtCore, QtGui
from .widgets import (
    ConfigWidget,
    ExpandingWidget,
    ModifiedIntSpinBox,
    ModifiedFloatSpinBox
)
from .lib import NOT_SET, AS_WIDGET, METADATA_KEY, TypeToKlass


class ConfigObject:
    default_state = ""
    _is_overriden = False
    _is_modified = False
    _was_overriden = False

    @property
    def is_modified(self):
        return self._is_modified or (self.was_overriden != self.is_overriden)

    @property
    def is_overriden(self):
        return self._is_overriden or self._parent.is_overriden

    @property
    def was_overriden(self):
        return self._was_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def any_parent_overriden(self):
        if self._parent._is_overriden:
            return True
        return self._parent.any_parent_overriden()

    @property
    def ignore_value_changes(self):
        return self._parent.ignore_value_changes

    @ignore_value_changes.setter
    def ignore_value_changes(self, value):
        self._parent.ignore_value_changes = value

    def item_value(self):
        raise NotImplementedError(
            "Method `item_value` not implemented!"
        )

    def config_value(self):
        return {self.key: self.item_value()}

    def value_from_values(self, values, keys=None):
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

    def style_state(self, is_overriden, is_modified):
        items = []
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

    def hierarchical_style_update(self):
        raise NotImplementedError(
            "Method `hierarchical_style_update` not implemented!"
        )


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

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self._is_overriden

    def reset_children_attributes(self):
        return


class BooleanWidget(ConfigWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self.is_group = input_data.get("is_group", False)

        self._state = None

        super(BooleanWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setAttribute(QtCore.Qt.WA_StyledBackground)
        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            label_widget.setAttribute(QtCore.Qt.WA_StyledBackground)
            layout.addWidget(label_widget, 0)

        layout.addWidget(self.checkbox, 1)

        value = NOT_SET
        if not self._as_widget:
            self.label_widget = label_widget
            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            default_value = input_data.get("default", NOT_SET)
            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.checkbox.setChecked(value)

            elif default_value is not NOT_SET:
                self.checkbox.setChecked(default_value)

        self.global_value = value
        self.start_value = self.item_value()
        self.override_value = NOT_SET

        self.checkbox.stateChanged.connect(self._on_value_change)

    def set_value(self, value, *, global_value=False):
        # Ignore value change because if `self.isChecked()` has same
        # value as `value` the `_on_value_change` is not triggered
        self.checkbox.setChecked(value)

        if global_value:
            self.global_value = self.item_value()

        self._on_value_change()

    def clear_value(self):
        self.set_value(False)

    def apply_overrides(self, override_value):
        self._is_modified = False
        self._state = None
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
        self.update_style()

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
        state = self.style_state(self.is_overriden, self.is_modified)
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


class IntegerWidget(ConfigWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self.is_group = input_data.get("is_group", False)

        self._state = None

        super(IntegerWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.int_input = ModifiedIntSpinBox()

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.int_input, 1)

        value = NOT_SET
        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.int_input.setValue(value)

        self.global_value = value
        self.start_value = self.item_value()
        self.override_value = NOT_SET

        self.int_input.valueChanged.connect(self._on_value_change)

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

    def apply_overrides(self, override_value):
        self._is_modified = False
        self._state = None
        self.override_value = override_value
        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            value = self.global_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self.set_value(value)
        self.update_style()

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self._is_modified = self.item_value() != self.global_value
        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(self.is_overriden, self.is_modified)
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


class FloatWidget(ConfigWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self.is_group = input_data.get("is_group", False)

        self._state = None

        super(FloatWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.float_input = ModifiedFloatSpinBox()

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

        value = NOT_SET
        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.float_input.setValue(value)

        self.start_value = self.item_value()
        self.global_value = value
        self.override_value = NOT_SET

        self.float_input.valueChanged.connect(self._on_value_change)

    def set_value(self, value, *, global_value=False):
        self.float_input.setValue(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.global_value)

    def apply_overrides(self, override_value):
        self._is_modified = False
        self._state = None
        self.override_value = override_value
        if override_value is NOT_SET:
            self._is_overriden = False
            value = self.start_value
        else:
            self._is_overriden = True
            value = override_value

        self.set_value(value)
        self.update_style()

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
        state = self.style_state(self.is_overriden, self.is_modified)
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


class TextSingleLineWidget(ConfigWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self.is_group = input_data.get("is_group", False)

        self._state = None

        super(TextSingleLineWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.text_input = QtWidgets.QLineEdit()

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.text_input, 1)

        value = NOT_SET
        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.text_input.setText(value)

        self.global_value = value
        self.start_value = self.item_value()
        self.override_value = NOT_SET

        self.text_input.textChanged.connect(self._on_value_change)

    def set_value(self, value, *, global_value=False):
        self.text_input.setText(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.start_value)

    def apply_overrides(self, override_value):
        self._is_modified = False
        self._state = None
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
        self.update_style()

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
        state = self.style_state(self.is_overriden, self.is_modified)
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


class TextMultiLineWidget(ConfigWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self.is_group = input_data.get("is_group", False)

        self._state = None

        super(TextMultiLineWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.text_input = QtWidgets.QPlainTextEdit()
        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.text_input, 1)

        value = NOT_SET
        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.text_input.setPlainText(value)

        self.global_value = value
        self.start_value = self.item_value()
        self.override_value = NOT_SET

        self.text_input.textChanged.connect(self._on_value_change)

    def set_value(self, value, *, global_value=False):
        self.text_input.setPlainText(value)
        if global_value:
            self.start_value = self.item_value()
            self.global_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.start_value)

    def apply_overrides(self, override_value):
        self._is_modified = False
        self._state = None
        self.override_value = override_value
        if override_value is NOT_SET:
            self._is_overriden = False
            value = self.start_value
        else:
            self._is_overriden = True
            value = override_value

        self.set_value(value)
        self.update_style()

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
        state = self.style_state(self.is_overriden, self.is_modified)
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
    value_changed = QtCore.Signal(object)
    tab_length = 4

    def __init__(self, *args, **kwargs):
        super(RawJsonInput, self).__init__(*args, **kwargs)
        self.setObjectName("RawJsonInput")
        self.setTabStopDistance(
            QtGui.QFontMetricsF(
                self.font()
            ).horizontalAdvance(" ") * self.tab_length
        )

        self._state = None
        self.is_valid = None
        self.textChanged.connect(self._on_value_change)

    def sizeHint(self):
        document = self.document()
        layout = document.documentLayout()

        height = document.documentMargin() + 2 * self.frameWidth() + 1
        block = document.begin()
        while block != document.end():
            height += layout.blockBoundingRect(block).height()
            block = block.next()

        value = super(RawJsonInput, self).sizeHint()
        value.setHeight(height)

        return value

    def set_value(self, value, *, global_value=False):
        if not isinstance(value, str):
            value = json.dumps(value, indent=4)
        self.setPlainText(value)

    def _on_value_change(self):
        self.validate()
        self.value_changed.emit(self)

    def validate_value(self, value):
        if isinstance(value, str) and not value:
            return True

        try:
            json.loads(value)
            return True
        except Exception:
            return False

    def update_style(self):
        if self.is_valid is None:
            return self.validate()

        if self.is_valid:
            state = ""
        else:
            state = "invalid"

        if self._state is None or self._state != state:
            self._state = state

            self.setProperty("state", state)
            self.style().polish(self)

    def resizeEvent(self, event):
        self.updateGeometry()
        super(RawJsonInput, self).resizeEvent(event)

    def item_value(self):
        return json.loads(self.toPlainText())

    def validate(self):
        value = self.toPlainText()
        self.is_valid = self.validate_value(value)
        self.update_style()


class RawJsonWidget(ConfigWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        self.is_group = input_data.get("is_group", False)

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

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget, 0)
        layout.addWidget(self.text_input, 1)

        value = NOT_SET
        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.text_input.set_value(value)

        self.global_value = value
        self.start_value = self.item_value()
        self.override_value = NOT_SET

        self.text_input.value_changed.connect(self._on_value_change)

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

    def apply_overrides(self, override_value):
        self._is_modified = False
        self._state = None
        self.override_value = override_value
        if override_value is NOT_SET:
            self._is_overriden = False
            value = self.start_value
        else:
            self._is_overriden = True
            value = override_value

        self.set_value(value)
        self.update_style()

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.text_input.is_valid:
            self._is_modified = self.item_value() != self.global_value
        else:
            self._is_modified = True

        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def update_style(self):
        state = self.style_state(self.is_overriden, self.is_modified)
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
        return self.text_input.item_value()


class TextListItem(QtWidgets.QWidget, ConfigObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(self, parent):
        super(TextListItem, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.text_input = QtWidgets.QLineEdit()
        self.add_btn = QtWidgets.QPushButton("+")
        self.remove_btn = QtWidgets.QPushButton("-")

        self.add_btn.setProperty("btn-type", "text-list")
        self.remove_btn.setProperty("btn-type", "text-list")

        layout.addWidget(self.text_input, 1)
        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)

        self.add_btn.setFixedSize(self._btn_size, self._btn_size)
        self.remove_btn.setFixedSize(self._btn_size, self._btn_size)
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.remove_btn.clicked.connect(self.on_remove_clicked)

        self.text_input.textChanged.connect(self._on_value_change)

        self.is_single = False

    def _on_value_change(self, item=None):
        self.value_changed.emit(self)

    def row(self):
        return self.parent().input_fields.index(self)

    def on_add_clicked(self):
        self.parent().add_row(row=self.row() + 1)

    def on_remove_clicked(self):
        if self.is_single:
            self.text_input.setText("")
        else:
            self.parent().remove_row(self)

    def config_value(self):
        return self.text_input.text()


class TextListSubWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)

    def __init__(self, input_data, values, parent_keys, parent):
        super(TextListSubWidget, self).__init__(parent)
        self.setObjectName("TextListSubWidget")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(3)
        self.setLayout(layout)

        self.input_fields = []
        self.add_row()

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        value = self.value_from_values(values)
        if value is not NOT_SET:
            self.set_value(value)

        self.global_value = value
        self.start_value = self.item_value()
        self.override_value = NOT_SET

    def set_value(self, value, *, global_value=False):
        previous_inputs = tuple(self.input_fields)
        for item_text in value:
            self.add_row(text=item_text)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if global_value:
            self.global_value = value
            self.start_value = self.item_value()
            self._on_value_change()

    def apply_overrides(self, override_value):
        self.override_value = override_value
        if override_value is NOT_SET:
            self._is_overriden = False
            value = self.start_value
        else:
            self._is_overriden = True
            value = override_value

        self.set_value(value)

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value([])

    def _on_value_change(self, item=None):
        self.value_changed.emit(self)

    def count(self):
        return len(self.input_fields)

    def add_row(self, row=None, text=None):
        # Create new item
        item_widget = TextListItem(self)

        # Set/unset if new item is single item
        current_count = self.count()
        if current_count == 0:
            item_widget.is_single = True
        elif current_count == 1:
            for _input_field in self.input_fields:
                _input_field.is_single = False

        item_widget.value_changed.connect(self._on_value_change)

        if row is None:
            self.layout().addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.layout().insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

        # Set text if entered text is not None
        # else (when add button clicked) trigger `_on_value_change`
        if text is not None:
            item_widget.text_input.setText(text)
        else:
            self._on_value_change()
        self.parent().updateGeometry()

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        self.layout().removeWidget(item_widget)
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

    def item_value(self):
        output = []
        for item in self.input_fields:
            text = item.config_value()
            if text:
                output.append(text)

        return output


class TextListWidget(ConfigWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        self.is_group = input_data.get("is_group", False)

        self._state = None

        super(TextListWidget, self).__init__(parent)
        self.setObjectName("TextListWidget")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget)

        self.label_widget = label_widget
        keys = list(parent_keys)
        keys.append(input_data["key"])
        self.keys = keys

        self.value_widget = TextListSubWidget(
            input_data, values, parent_keys, self
        )
        self.value_widget.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.value_widget.value_changed.connect(self._on_value_change)

        # self.value_widget.se
        self.key = input_data["key"]
        layout.addWidget(self.value_widget)
        self.setLayout(layout)

    @property
    def start_value(self):
        return self.value_widget.start_value

    @property
    def global_value(self):
        return self.value_widget.global_value

    @property
    def override_value(self):
        return self.value_widget.override_value

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return
        self._is_modified = self.item_value() != self.global_value
        if self.is_overidable:
            self._is_overriden = True

        self.update_style()

        self.value_changed.emit(self)

    def set_value(self, value, *, global_value=False):
        self.value_widget.set_value(value, global_value=global_value)
        if global_value:
            self._on_value_change()

    def reset_value(self):
        self.value_widget.reset_value()

    def clear_value(self):
        self.value_widget.clear_value()

    def apply_overrides(self, override_value):
        self.value_widget.apply_overrides(override_value)
        self._is_modified = False
        self._state = None
        self.update_style()

    def update_style(self):
        state = self.style_state(self.is_overriden, self.is_modified)
        if self._state == state:
            return

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        return self.value_widget.config_value()


class ModifiableDictItem(QtWidgets.QWidget, ConfigObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(self, object_type, parent):
        self._parent = parent

        super(ModifiableDictItem, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        ItemKlass = TypeToKlass.types[object_type]

        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setObjectName("DictKey")

        self.value_input = ItemKlass(
            {},
            AS_WIDGET,
            [],
            self,
            None
        )
        self.add_btn = QtWidgets.QPushButton("+")
        self.remove_btn = QtWidgets.QPushButton("-")

        self.add_btn.setProperty("btn-type", "text-list")
        self.remove_btn.setProperty("btn-type", "text-list")

        layout.addWidget(self.key_input, 0)
        layout.addWidget(self.value_input, 1)
        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)

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
        return self.parent().input_fields.index(self)

    def on_add_clicked(self):
        self.parent().add_row(row=self.row() + 1)

    def on_remove_clicked(self):
        if self.is_single:
            self.value_input.clear_value()
            self.key_input.setText("")
        else:
            self.parent().remove_row(self)

    def config_value(self):
        key = self.key_input.text()
        value = self.value_input.item_value()
        if not key:
            return {}
        return {key: value}


class ModifiableDictSubWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)

    def __init__(self, input_data, values, parent_keys, parent):
        self._parent = parent

        super(ModifiableDictSubWidget, self).__init__(parent)
        self.setObjectName("ModifiableDictSubWidget")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 0, 5)
        layout.setSpacing(5)
        self.setLayout(layout)

        self.input_fields = []
        self.object_type = input_data["object_type"]

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        value = self.value_from_values(values)
        if value is not NOT_SET:
            for item_key, item_value in value.items():
                self.add_row(key=item_key, value=item_value)

        if self.count() == 0:
            self.add_row()

        self.global_value = value
        self.start_value = self.config_value()
        self.override_value = NOT_SET

    @property
    def is_group(self):
        return self._parent.is_group

    @property
    def any_parent_is_group(self):
        return self._parent.any_parent_is_group

    def _on_value_change(self, item=None):
        self.value_changed.emit(self)

    def count(self):
        return len(self.input_fields)

    def add_row(self, row=None, key=None, value=None):
        # Create new item
        item_widget = ModifiableDictItem(self.object_type, self)

        # Set/unset if new item is single item
        current_count = self.count()
        if current_count == 0:
            item_widget.is_single = True
        elif current_count == 1:
            for _input_field in self.input_fields:
                _input_field.is_single = False

        item_widget.value_changed.connect(self._on_value_change)

        if row is None:
            self.layout().addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.layout().insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

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

        self.layout().removeWidget(item_widget)
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

    def config_value(self):
        output = {}
        for item in self.input_fields:
            item_value = item.config_value()
            if item_value:
                output.update(item_value)
        return output


class ModifiableDict(ExpandingWidget, InputObject):
    # Should be used only for dictionary with one datatype as value
    # TODO this is actually input field (do not care if is group or not)
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, values, parent_keys, parent,
        label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self.is_group = input_data.get("is_group", False)
        self._state = None

        super(ModifiableDict, self).__init__(input_data["label"], parent)
        self.setObjectName("ModifiableDict")

        self.value_widget = ModifiableDictSubWidget(
            input_data, values, parent_keys, self
        )
        self.value_widget.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.value_widget.value_changed.connect(self._on_value_change)

        self.set_content_widget(self.value_widget)

        self.key = input_data["key"]

        self.global_value = self.item_value()
        self.override_value = NOT_SET

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

    def apply_overrides(self, override_value):
        self._state = None
        self._is_modified = False
        self.override_value = override_value
        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            value = self.global_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self.set_value(value)
        self.update_style()

    def update_style(self):
        state = self.style_state(self.is_overriden, self.is_modified)
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
        return self.value_widget.config_value()


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

        self.is_group = input_data.get("is_group", False)

        self._state = None
        self._child_state = None

        super(DictExpandWidget, self).__init__(input_data["label"], parent)

        content_widget = QtWidgets.QWidget(self)
        content_widget.setVisible(False)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 0, 3)

        self.set_content_widget(content_widget)

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

    def apply_overrides(self, override_value):
        # Make sure this is set to False
        self._is_overriden = False
        self._state = None
        self._child_state = None
        for item in self.input_fields:
            if override_value is NOT_SET:
                child_value = NOT_SET
            else:
                child_value = override_value.get(item.key, NOT_SET)

            item.apply_overrides(child_value)

        self._is_overriden = (
            self.is_group
            and self.is_overidable
            and (
                override_value is not NOT_SET
                or self.child_overriden
            )
        )
        self._was_overriden = bool(self._is_overriden)
        self.update_style()

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
        child_state = self.style_state(self.child_overriden, child_modified)
        if child_state:
            child_state = "child-{}".format(child_state)

        if child_state != self._child_state:
            self.setProperty("state", child_state)
            self.style().polish(self)
            self._child_state = child_state

        state = self.style_state(self.is_overriden, self.is_modified)
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
            if input_field.child_overriden:
                return True
        return False

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


class DictWidget(ConfigWidget, ConfigObject):
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

        self.is_group = input_data.get("is_group", False)

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

    def apply_overrides(self, override_value):
        # Make sure this is set to False
        self._is_overriden = False
        self._state = None
        self._child_state = None
        for item in self.input_fields:
            if override_value is NOT_SET:
                child_value = NOT_SET
            else:
                child_value = override_value.get(item.key, NOT_SET)

            item.apply_overrides(child_value)

        self._is_overriden = (
            self.is_group
            and self.is_overidable
            and (
                override_value is not NOT_SET
                or self.child_overriden
            )
        )
        self.update_style()

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
        child_state = self.style_state(self.child_overriden, child_modified)
        if child_state:
            child_state = "child-{}".format(child_state)

        if child_state != self._child_state:
            self.setProperty("state", child_state)
            self.style().polish(self)
            self._child_state = child_state

        state = self.style_state(self.is_overriden, self.is_modified)
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
            if input_field.child_overriden:
                return True
        return False

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


class DictInvisible(ConfigWidget, ConfigObject):
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
        self.is_group = input_data.get("is_group", False)

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
            if input_field.child_overriden:
                return True
        return False

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

    def apply_overrides(self, override_value):
        self._is_overriden = False
        for item in self.input_fields:
            if override_value is NOT_SET:
                child_value = NOT_SET
            else:
                child_value = override_value.get(item.key, NOT_SET)
            item.apply_overrides(child_value)

        self._is_overriden = (
            self.is_group
            and self.is_overidable
            and (
                override_value is not None
                or self.child_overriden
            )
        )
        self.update_style()

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
class DictFormWidget(ConfigWidget, ConfigObject):
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

        self.is_group = False

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

    def discard_changes(self):
        for item in self.input_fields.values():
            item.discard_changes()

        self._is_modified = self.child_modified
        self._is_overriden = self._was_overriden

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
            if input_field.child_overriden:
                return True
        return False

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
TypeToKlass.types["list-text"] = TextListWidget
