import json
import logging
import collections
from Qt import QtWidgets, QtCore, QtGui
from .widgets import (
    AbstractConfigObject,
    ExpandingWidget,
    NumberSpinBox,
    PathInput
)
from .lib import NOT_SET, METADATA_KEY, TypeToKlass, CHILD_OFFSET


class ConfigObject(AbstractConfigObject):
    allow_actions = True

    default_state = ""

    _has_studio_override = True
    _as_widget = False
    _is_overriden = False
    _is_modified = False
    _was_overriden = False
    _is_invalid = False
    _is_group = False
    _is_nullable = False

    _log = None

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def has_studio_override(self):
        return self._has_studio_override

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
        if self._as_widget:
            return self._parent.was_overriden
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
    def is_nullable(self):
        return self._is_nullable

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
        return self._parent.ignore_value_changes

    @ignore_value_changes.setter
    def ignore_value_changes(self, value):
        """Setter for global parent item to apply changes for all inputs."""
        self._parent.ignore_value_changes = value

    def config_value(self):
        """Output for saving changes or overrides."""
        return {self.key: self.item_value()}

    @classmethod
    def style_state(cls, is_invalid, is_overriden, is_modified):
        items = []
        if is_invalid:
            items.append("invalid")
        else:
            if is_overriden:
                items.append("overriden")
            if is_modified:
                items.append("modified")
        return "-".join(items) or cls.default_state

    def _discard_changes(self):
        self.ignore_value_changes = True
        self.discard_changes()
        self.ignore_value_changes = False

    def _remove_overrides(self):
        self.ignore_value_changes = True
        self.remove_overrides()
        self.ignore_value_changes = False

    def _set_as_overriden(self):
        self.ignore_value_changes = True
        self.set_as_overriden()
        self.ignore_value_changes = False

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
        self._is_overriden = self._was_overriden
        if (
            self.is_overidable
            and self._was_overriden
            and self.override_value is not NOT_SET
        ):
            self.set_value(self.override_value)
        else:
            self.set_value(self.start_value)

        if not self.is_overidable:
            self._is_modified = self.studio_value != self.item_value()
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
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(BooleanWidget, self).__init__(parent_widget)

        self._parent = parent
        self._as_widget = as_widget
        self._state = None

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)
        self.default_value = input_data.get("default", NOT_SET)

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                layout.addWidget(label_widget, 0)
            self.label_widget = label_widget

        self.checkbox = QtWidgets.QCheckBox(self)
        spacer = QtWidgets.QWidget(self)
        layout.addWidget(self.checkbox, 0)
        layout.addWidget(spacer, 1)

        spacer.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setFocusProxy(self.checkbox)

        self.checkbox.stateChanged.connect(self._on_value_change)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if value is not NOT_SET:
            self.set_value(value)

        elif self.default_value is not NOT_SET:
            self.set_value(self.default_value)

        self.studio_value = value
        self.start_value = self.item_value()

        self._is_modified = self.studio_value != self.start_value

    def set_value(self, value):
        # Ignore value change because if `self.isChecked()` has same
        # value as `value` the `_on_value_change` is not triggered
        self.checkbox.setChecked(value)

    def clear_value(self):
        self.set_value(False)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

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


class NumberWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)
    input_modifiers = ("minimum", "maximum", "decimal")

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(NumberWidget, self).__init__(parent_widget)

        self._parent = parent
        self._as_widget = as_widget
        self._state = None

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)
        self.default_value = input_data.get("default", NOT_SET)

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

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

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        else:
            if parent_values is not NOT_SET:
                value = parent_values.get(self.key, NOT_SET)

        if value is not NOT_SET:
            self.set_value(value)

        elif self.default_value is not NOT_SET:
            self.set_value(self.default_value)

        self.studio_value = value
        self.start_value = self.item_value()

        self._is_modified = self.studio_value != self.start_value

    def set_value(self, value):
        self.input_field.setValue(value)

    def clear_value(self):
        self.set_value(0)

    def reset_value(self):
        self.set_value(self.start_value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

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
            widget = self.input_field
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.input_field.value()


class TextWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(TextWidget, self).__init__(parent_widget)

        self._parent = parent
        self._as_widget = as_widget
        self._state = None

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)
        self.default_value = input_data.get("default", NOT_SET)

        self.multiline = input_data.get("multiline", False)

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if self.multiline:
            self.text_input = QtWidgets.QPlainTextEdit(self)
        else:
            self.text_input = QtWidgets.QLineEdit(self)

        self.setFocusProxy(self.text_input)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0)
            self.label_widget = label_widget

        layout.addWidget(self.text_input, 1)

        self.text_input.textChanged.connect(self._on_value_change)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if value is not NOT_SET:
            self.set_value(value)

        elif self.default_value is not NOT_SET:
            self.set_value(self.default_value)

        self.studio_value = value
        self.start_value = self.item_value()

        self._is_modified = self.studio_value != self.start_value

    def set_value(self, value):
        if self.multiline:
            self.text_input.setPlainText(value)
        else:
            self.text_input.setText(value)

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value("")

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

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
        if self.multiline:
            return self.text_input.toPlainText()
        else:
            return self.text_input.text()


class PathInputWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(PathInputWidget, self).__init__(parent_widget)

        self._parent = parent
        self._as_widget = as_widget
        self._state = None

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)
        self.default_value = input_data.get("default", NOT_SET)

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

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

        self.path_input = PathInput(self)
        self.setFocusProxy(self.path_input)
        layout.addWidget(self.path_input, 1)

        self.path_input.textChanged.connect(self._on_value_change)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if value is not NOT_SET:
            self.set_value(value)

        elif self.default_value is not NOT_SET:
            self.set_value(self.default_value)

        self.studio_value = value
        self.start_value = self.item_value()

        self._is_modified = self.studio_value != self.start_value

    def set_value(self, value):
        self.path_input.setText(value)

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value("")

    def focusOutEvent(self, event):
        self.path_input.clear_end_path()
        super(PathInput, self).focusOutEvent(event)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self._is_invalid:
            self._is_modified = True
        elif self.is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

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
            widget = self.path_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.path_input.text()


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
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(RawJsonWidget, self).__init__(parent_widget)

        self._parent = parent
        self._as_widget = as_widget
        self._state = None

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)
        self.default_value = input_data.get("default", NOT_SET)

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text_input = RawJsonInput(self)
        self.text_input.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.setFocusProxy(self.text_input)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0)
            self.label_widget = label_widget
        layout.addWidget(self.text_input, 1)

        self.text_input.textChanged.connect(self._on_value_change)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if value is not NOT_SET:
            self.set_value(value)

        elif self.default_value is not NOT_SET:
            self.set_value(self.default_value)

        self._is_invalid = self.text_input.has_invalid_value()

        self.studio_value = value
        self.start_value = self.item_value()

        self._is_modified = self.studio_value != self.start_value

    def set_value(self, value):
        self.text_input.set_value(value)

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value("")

    def _on_value_change(self, item=None):
        self._is_invalid = self.text_input.has_invalid_value()
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

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
            self,
            as_widget=True,
            label_widget=None
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


class ListWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ListWidget, self).__init__(parent_widget)
        self.setObjectName("ListWidget")

        self._parent = parent
        self._state = None
        self._as_widget = as_widget

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)

        self.object_type = input_data["object_type"]
        self.default_value = input_data.get("default", NOT_SET)
        self.input_modifiers = input_data.get("input_modifiers") or {}

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

        self.key = input_data["key"]

        self.input_fields = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget)
        self.label_widget = label_widget

        inputs_widget = QtWidgets.QWidget(self)
        inputs_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        layout.addWidget(inputs_widget)

        inputs_layout = QtWidgets.QVBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 5, 0, 5)
        inputs_layout.setSpacing(3)

        self.inputs_widget = inputs_widget
        self.inputs_layout = inputs_layout

        self.add_row(is_empty=True)

    def count(self):
        return len(self.input_fields)

    def reset_value(self):
        self.set_value(self.start_value)

    def clear_value(self):
        self.set_value([])

    def update_studio_values(self, parent_values):
        old_inputs = tuple(self.input_fields)

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        self.studio_value = value

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

        self._is_modified = self.studio_value != self.start_value
        self.hierarchical_style_update()

    def set_value(self, value):
        previous_inputs = tuple(self.input_fields)
        for item_value in value:
            self.add_row(value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

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
            item_widget.value_input.update_studio_values(value)
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
        self._is_modified = False
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

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

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
        super(ModifiableDictItem, self).__init__(parent)

        self._parent = config_parent

        self.is_single = False
        self.is_key_duplicated = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        ItemKlass = TypeToKlass.types[object_type]

        self.key_input = QtWidgets.QLineEdit(self)
        self.key_input.setObjectName("DictKey")

        self.value_input = ItemKlass(
            input_modifiers,
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

        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)
        layout.addWidget(self.key_input, 0)
        layout.addWidget(self.value_input, 1)

        self.setFocusProxy(self.value_input)

        self.add_btn.setFixedSize(self._btn_size, self._btn_size)
        self.remove_btn.setFixedSize(self._btn_size, self._btn_size)
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.remove_btn.clicked.connect(self.on_remove_clicked)

        self.key_input.textChanged.connect(self._on_value_change)
        self.value_input.value_changed.connect(self._on_value_change)

        self.origin_key = self.key_value()

    def key_value(self):
        return self.key_input.text()

    def is_key_invalid(self):
        if self.key_value() == "":
            return True

        if self.is_key_duplicated:
            return True
        return False

    def _on_value_change(self, item=None):
        self.update_style()
        self.value_changed.emit(self)

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
        if self.value_input.isEnabled():
            self._parent.add_row(row=self.row() + 1)
        else:
            self.set_as_empty(False)

    def on_remove_clicked(self):
        self._parent.remove_row(self)

    def set_as_empty(self, is_empty=True):
        self.key_input.setEnabled(not is_empty)
        self.value_input.setEnabled(not is_empty)
        self.remove_btn.setEnabled(not is_empty)
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
        return self.is_key_invalid() or self.value_input.is_invalid

    def update_style(self):
        if self.is_key_invalid():
            state = "invalid"
        elif self.is_key_modified():
            state = "modified"
        else:
            state = ""

        self.key_input.setProperty("state", state)
        self.key_input.style().polish(self.key_input)

    def row(self):
        return self._parent.input_fields.index(self)

    def config_value(self):
        key = self.key_input.text()
        value = self.value_input.item_value()
        return {key: value}

    def mouseReleaseEvent(self, event):
        return QtWidgets.QWidget.mouseReleaseEvent(self, event)


class ModifiableDict(QtWidgets.QWidget, InputObject):
    # Should be used only for dictionary with one datatype as value
    # TODO this is actually input field (do not care if is group or not)
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ModifiableDict, self).__init__(parent_widget)
        self.setObjectName("ModifiableDict")

        self._parent = parent
        self._state = None
        self._as_widget = as_widget

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)

        self.input_fields = []

        self.key = input_data["key"]

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 3, 0, 3)

        if as_widget:
            main_layout.addWidget(content_widget)
        else:
            body_widget = ExpandingWidget(input_data["label"], self)
            main_layout.addWidget(body_widget)
            body_widget.set_content_widget(content_widget)

            self.body_widget = body_widget
            self.label_widget = body_widget.label_widget

            expandable = input_data.get("expandable", True)
            if not expandable:
                body_widget.hide_toolbox(hide_content=False)
            else:
                expanded = input_data.get("expanded", False)
                if expanded:
                    body_widget.toggle_content()

        self.content_widget = content_widget
        self.content_layout = content_layout

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.object_type = input_data["object_type"]
        self.default_value = input_data.get("default", NOT_SET)
        self.input_modifiers = input_data.get("input_modifiers") or {}

        self.add_row(is_empty=True)

    def count(self):
        return len(self.input_fields)

    def update_studio_values(self, parent_values):
        old_inputs = tuple(self.input_fields)

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        self.studio_value = value

        if value is not NOT_SET:
            for item_key, item_value in value.items():
                self.add_row(key=item_key, value=item_value)

        elif self.default_value is not NOT_SET:
            for item_key, item_value in self.default_value.items():
                self.add_row(key=item_key, value=item_value)

        for old_input in old_inputs:
            self.remove_row(old_input)

        if self.count() == 0:
            self.add_row(is_empty=True)

        self.start_value = self.item_value()

        self._is_modified = self.studio_value != self.start_value

    def set_value(self, value):
        previous_inputs = tuple(self.input_fields)
        for item_key, item_value in value.items():
            self.add_row(key=item_key, value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

    def _on_value_change(self, item=None):
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

        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self.is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

        self.update_style()

        self.value_changed.emit(self)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
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

        if not self._as_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

        self._state = state

    def item_value(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())
        return output

    def add_row(self, row=None, key=None, value=None, is_empty=False):
        # Create new item
        item_widget = ModifiableDictItem(
            self.object_type, self.input_modifiers, self, self.content_widget
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
            if self._is_overriden:
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
class DictWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if as_widget:
            raise TypeError("Can't use \"{}\" as widget item.".format(
                self.__class__.__name__
            ))

        if parent_widget is None:
            parent_widget = parent
        super(DictWidget, self).__init__(parent_widget)
        self.setObjectName("DictWidget")

        self._state = None
        self._child_state = None

        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group
        self.any_parent_is_group = any_parent_is_group

        self._is_group = input_data.get("is_group", False)
        self._is_nullable = input_data.get("is_nullable", False)

        if input_data.get("highlight_content", False):
            content_state = "hightlighted"
            bottom_margin = 5
        else:
            content_state = ""
            bottom_margin = 0

        self.input_fields = []

        self.key = input_data["key"]

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        body_widget = ExpandingWidget(input_data["label"], self)

        main_layout.addWidget(body_widget)

        content_widget = QtWidgets.QWidget(body_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", content_state)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, bottom_margin)

        body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        self.label_widget = body_widget.label_widget

        self.checkbox_widget = None
        self.checkbox_key = input_data.get("checkbox_key")

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

        expandable = input_data.get("expandable", True)
        if len(self.input_fields) == 1 and self.checkbox_widget:
            body_widget.hide_toolbox(hide_content=True)

        elif expandable:
            expanded = input_data.get("expanded", False)
            if expanded:
                body_widget.toggle_content()
        else:
            body_widget.hide_toolbox(hide_content=False)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)
        if self.checkbox_key and not self.checkbox_widget:
            key = child_configuration.get("key")
            if key == self.checkbox_key:
                return self._add_checkbox_child(child_configuration)

        item = klass(child_configuration, self)
        item.value_changed.connect(self._on_value_change)
        self.content_layout.addWidget(item)

        self.input_fields.append(item)
        return item

    def _add_checkbox_child(self, child_configuration):
        item = BooleanWidget(
            child_configuration, self, label_widget=self.label_widget
        )
        item.value_changed.connect(self._on_value_change)

        self.body_widget.add_widget_after_label(item)
        self.checkbox_widget = item
        self.input_fields.append(item)
        return item

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for item in self.input_fields:
            item.remove_overrides()

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._is_modified = False

        for item in self.input_fields:
            item.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

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

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group:
            if self.is_overidable:
                self._is_overriden = True

            self.hierarchical_style_update()

        self.value_changed.emit(self)

        self.update_style()

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self, is_overriden=None):
        child_modified = self.child_modified
        child_invalid = self.child_invalid
        child_state = self.style_state(
            child_invalid, self.child_overriden, child_modified
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
            return self._is_modified or self.child_modified
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
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(DictInvisible, self).__init__(parent_widget)
        self.setObjectName("DictInvisible")

        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group
        self._is_group = input_data.get("is_group", False)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.input_fields = []

        self.key = input_data["key"]

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        item = klass(child_configuration, self)
        self.layout().addWidget(item)

        item.value_changed.connect(self._on_value_change)

        self.input_fields.append(item)
        return item

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

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group:
            if self.is_overidable:
                self._is_overriden = True
            self.hierarchical_style_update()

        self.value_changed.emit(self)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for item in self.input_fields:
            item.remove_overrides()

    def discard_changes(self):
        self._is_modified = False
        self._is_overriden = self._was_overriden

        for item in self.input_fields:
            item.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

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


class PathWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)

    platforms = ("windows", "darwin", "linux")
    platform_labels_mapping = {
        "windows": "Windows",
        "darwin": "MacOS",
        "linux": "Linux"
    }
    # TODO be able to save and load with separators
    platform_separators = {
        "windows": ";",
        "darwin": ":",
        "linux": ":"
    }

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(PathWidget, self).__init__(parent_widget)

        self._parent = parent
        self._state = None
        self._child_state = None
        self._as_widget = as_widget

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group
        self.any_parent_is_group = any_parent_is_group

        # This is partial input and dictionary input
        if not any_parent_is_group and not as_widget:
            self._is_group = True
        else:
            self._is_group = False
        self._is_nullable = input_data.get("is_nullable", False)

        self.default_value = input_data.get("default", NOT_SET)
        self.multiplatform = input_data.get("multiplatform", False)
        self.multipath = input_data.get("multipath", False)

        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET
        self.start_value = NOT_SET

        self.input_fields = []

        if not self.multiplatform and not self.multipath:
            layout = QtWidgets.QHBoxLayout(self)
        else:
            layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                layout.addWidget(label_widget, 0)
            self.label_widget = label_widget

        self.content_widget = QtWidgets.QWidget(self)
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.content_widget)

        self.create_gui()

    def create_gui(self):
        if not self.multiplatform and not self.multipath:
            input_data = {"key": self.key}
            path_input = PathInputWidget(
                input_data, self, label_widget=self.label_widget
            )
            self.setFocusProxy(path_input)
            self.content_layout.addWidget(path_input)
            self.input_fields.append(path_input)
            path_input.value_changed.connect(self._on_value_change)
            return

        input_data_for_list = {
            "object_type": "path-input"
        }
        if not self.multiplatform:
            input_data_for_list["key"] = self.key
            input_widget = ListWidget(
                input_data_for_list, self, label_widget=self.label_widget
            )
            self.setFocusProxy(input_widget)
            self.content_layout.addWidget(input_widget)
            self.input_fields.append(input_widget)
            input_widget.value_changed.connect(self._on_value_change)
            return

        proxy_widget = QtWidgets.QWidget(self.content_widget)
        proxy_layout = QtWidgets.QFormLayout(proxy_widget)
        for platform_key in self.platforms:
            platform_label = self.platform_labels_mapping[platform_key]
            label_widget = QtWidgets.QLabel(platform_label, proxy_widget)
            if self.multipath:
                input_data_for_list["key"] = platform_key
                input_widget = ListWidget(
                    input_data_for_list, self, label_widget=label_widget
                )
            else:
                input_data = {"key": platform_key}
                input_widget = PathInputWidget(
                    input_data, self, label_widget=label_widget
                )
            proxy_layout.addRow(label_widget, input_widget)
            self.input_fields.append(input_widget)
            input_widget.value_changed.connect(self._on_value_change)

        self.setFocusProxy(self.input_fields[0])
        self.content_layout.addWidget(proxy_widget)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if not self.multiplatform:
            self.input_fields[0].update_studio_values(parent_values)

        elif self.multiplatform:
            for input_field in self.input_fields:
                input_field.update_studio_values(value)

        self.studio_value = value
        self.start_value = self.item_value()
        self._is_modified = self.studio_value != self.start_value

    def apply_overrides(self, parent_values):
        self._is_modified = False
        self._state = None
        self._child_state = None
        override_values = NOT_SET
        if self._as_widget:
            override_values = parent_values
        elif parent_values is not NOT_SET:
            override_values = parent_values.get(self.key, override_values)

        self._is_overriden = override_values is not NOT_SET
        self._was_overriden = bool(self._is_overriden)

        if not self.multiplatform:
            self.input_fields[0].apply_overrides(parent_values)
        else:
            for input_field in self.input_fields:
                input_field.apply_overrides(override_values)

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
            self.input_fields[0].set_value(value)

        else:
            for input_field in self.input_fields:
                _value = value[input_field.key]
                input_field.set_value(_value)

    def reset_value(self):
        for input_field in self.input_fields:
            input_field.reset_value()

    def clear_value(self):
        for input_field in self.input_fields:
            input_field.clear_value()

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        else:
            self._is_modified = self.item_value() != self.studio_value

        self.hierarchical_style_update()

        self.value_changed.emit(self)

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

        if not self._as_widget:
            state = self.style_state(
                child_invalid, self.is_overriden, self.is_modified
            )
            if self._state == state:
                return

            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

            self._state = state

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for item in self.input_fields:
            item.remove_overrides()

    def discard_changes(self):
        self._is_modified = False
        self._is_overriden = self._was_overriden

        for input_field in self.input_fields:
            input_field.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        self._is_overriden = True

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

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def item_value(self):
        if not self.multiplatform and not self.multipath:
            return self.input_fields[0].item_value()

        if not self.multiplatform:
            return self.input_fields[0].item_value()

        output = {}
        for input_field in self.input_fields:
            output.update(input_field.config_value())
        return output

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        value = self.item_value()
        if not self.multiplatform:
            value = {self.key: value}
        return value, self.is_group


# Proxy for form layout
class FormLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super(FormLabel, self).__init__(*args, **kwargs)
        self.item = None


class DictFormWidget(QtWidgets.QWidget, ConfigObject):
    value_changed = QtCore.Signal(object)
    allow_actions = False

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(DictFormWidget, self).__init__(parent_widget)

        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

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
        for item in self.input_fields:
            item.remove_overrides()

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

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


TypeToKlass.types["boolean"] = BooleanWidget
TypeToKlass.types["number"] = NumberWidget
TypeToKlass.types["text"] = TextWidget
TypeToKlass.types["path-input"] = PathInputWidget
TypeToKlass.types["raw-json"] = RawJsonWidget
TypeToKlass.types["list"] = ListWidget
TypeToKlass.types["dict-modifiable"] = ModifiableDict
TypeToKlass.types["dict"] = DictWidget
TypeToKlass.types["dict-invisible"] = DictInvisible
TypeToKlass.types["path-widget"] = PathWidget
TypeToKlass.types["dict-form"] = DictFormWidget
