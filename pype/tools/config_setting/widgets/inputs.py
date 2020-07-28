import json
from Qt import QtWidgets, QtCore
from . import config
from .base import PypeConfigurationWidget, TypeToKlass
from .widgets import (
    ClickableWidget,
    ExpandingWidget,
    ModifiedIntSpinBox,
    ModifiedFloatSpinBox
)
from .lib import NOT_SET, AS_WIDGET


class SchemeGroupHierarchyBug(Exception):
    def __init__(self, msg=None):
        if not msg:
            # TODO better message
            msg = "SCHEME BUG: Attribute `is_group` is mixed in the hierarchy"
        super(SchemeGroupHierarchyBug, self).__init(msg)


class BooleanWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._as_widget = values is AS_WIDGET
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        if not any_parent_is_group and not is_group:
            is_group = True

        self.is_group = is_group
        self.is_modified = False
        self.is_overriden = False

        super(BooleanWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setAttribute(QtCore.Qt.WA_StyledBackground)
        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            label_widget.setAttribute(QtCore.Qt.WA_StyledBackground)
            layout.addWidget(label_widget)

        layout.addWidget(self.checkbox)

        if not self._as_widget:
            self.label_widget = label_widget
            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.checkbox.setChecked(value)

        self.origin_value = self.item_value()

        self.checkbox.stateChanged.connect(self._on_value_change)

    def set_value(self, value, origin_value=False):
        self.checkbox.setChecked(value)
        if origin_value:
            self.origin_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.origin_value)

    def clear_value(self):
        self.reset_value()

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def _on_value_change(self, value=None):
        self.is_modified = self.item_value() != self.origin_value
        self.is_overriden = True

        self._update_style()

        self.value_changed.emit()

    def _update_style(self):
        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

        if self._as_widget:
            property_name = "input-state"
        else:
            property_name = "state"

        self.label_widget.setProperty(property_name, state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        return self.checkbox.isChecked()

    def config_value(self):
        return {self.key: self.item_value()}


class IntegerWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        if not any_parent_is_group and not is_group:
            is_group = True

        self.is_group = is_group
        self.is_modified = False
        self.is_overriden = False

        super(IntegerWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.int_input = ModifiedIntSpinBox()

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget)
        layout.addWidget(self.int_input)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.int_input.setValue(value)

        self.origin_value = self.item_value()

        self.int_input.valueChanged.connect(self._on_value_change)

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def set_value(self, value, origin_value=False):
        self.int_input.setValue(value)
        if origin_value:
            self.origin_value = self.item_value()
            self._on_value_change()

    def clear_value(self):
        self.set_value(0)

    def reset_value(self):
        self.set_value(self.origin_value)

    def _on_value_change(self, value=None):
        self.is_modified = self.item_value() != self.origin_value
        self.is_overriden = True

        self._update_style()

        self.value_changed.emit()

    def _update_style(self):
        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

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

    def config_value(self):
        return {self.key: self.item_value()}


class FloatWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        if not any_parent_is_group and not is_group:
            is_group = True

        self.is_group = is_group
        self.is_modified = False
        self.is_overriden = False

        super(FloatWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

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
            layout.addWidget(label_widget)
        layout.addWidget(self.float_input)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.float_input.setValue(value)

        self.origin_value = self.item_value()

        self.float_input.valueChanged.connect(self._on_value_change)

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def set_value(self, value, origin_value=False):
        self.float_input.setValue(value)
        if origin_value:
            self.origin_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.origin_value)

    def clear_value(self):
        self.set_value(0)

    def _on_value_change(self, value=None):
        self.is_modified = self.item_value() != self.origin_value
        self.is_overriden = True

        self._update_style()

        self.value_changed.emit()

    def _update_style(self):
        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

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

    def config_value(self):
        return {self.key: self.item_value()}


class TextSingleLineWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent
        self._as_widget = values is AS_WIDGET

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        if not any_parent_is_group and not is_group:
            is_group = True

        self.is_group = is_group
        self.is_modified = False
        self.is_overriden = False

        super(TextSingleLineWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text_input = QtWidgets.QLineEdit()

        if not self._as_widget and not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget)
        layout.addWidget(self.text_input)

        if not self._as_widget:
            self.label_widget = label_widget

            self.key = input_data["key"]
            keys = list(parent_keys)
            keys.append(self.key)
            self.keys = keys

            value = self.value_from_values(values)
            if value is not NOT_SET:
                self.text_input.setText(value)

        self.origin_value = self.item_value()

        self.text_input.textChanged.connect(self._on_value_change)

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def set_value(self, value, origin_value=False):
        self.text_input.setText(value)
        if origin_value:
            self.origin_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.origin_value)

    def clear_value(self):
        self.set_value("")

    def _on_value_change(self, value=None):
        self.is_modified = self.item_value() != self.origin_value
        self.is_overriden = True

        self._update_style()

        self.value_changed.emit()

    def _update_style(self):
        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

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

    def config_value(self):
        return {self.key: self.item_value()}


class TextMultiLineWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        if not any_parent_is_group and not is_group:
            is_group = True

        self.is_group = is_group
        self.is_modified = False
        self.is_overriden = False

        super(TextMultiLineWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text_input = QtWidgets.QPlainTextEdit()
        if not label_widget:
            label = input_data["label"]
            label_widget = QtWidgets.QLabel(label)
            layout.addWidget(label_widget)
        layout.addWidget(self.text_input)

        self.label_widget = label_widget

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        value = self.value_from_values(values)
        if value is not NOT_SET:
            self.text_input.setPlainText(value)

        self.origin_value = self.item_value()

        self.text_input.textChanged.connect(self._on_value_change)

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def set_value(self, value, origin_value=False):
        self.text_input.setPlainText(value)
        if origin_value:
            self.origin_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.origin_value)

    def clear_value(self):
        self.set_value("")

    def _on_value_change(self, value=None):
        self.is_modified = self.item_value() != self.origin_value
        self.is_overriden = True

        self._update_style()

        self.value_changed.emit()

    def _update_style(self):
        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

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

    def config_value(self):
        return {self.key: self.item_value()}


class TextListItem(QtWidgets.QWidget, PypeConfigurationWidget):
    _btn_size = 20
    value_changed = QtCore.Signal()

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

    def _on_value_change(self):
        self.value_changed.emit()

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


class TextListSubWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(self, input_data, values, parent_keys, parent):
        super(TextListSubWidget, self).__init__(parent)
        self.setObjectName("TextListSubWidget")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
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

        self.origin_value = self.item_value()

    def set_value(self, value, origin_value=False):
        for input_field in self.input_fields:
            self.remove_row(input_field)

        for item_text in value:
            self.add_row(text=item_text)

        if origin_value:
            self.origin_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.origin_value)

    def clear_value(self):
        self.set_value([])

    def _on_value_change(self):
        self.value_changed.emit()

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

    def config_value(self):
        return {self.key: self.item_value()}


class TextListWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        self.is_modified = False
        self.is_group = is_group
        self.is_overriden = False

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
        # keys = list(parent_keys)
        # keys.append(input_data["key"])
        # self.keys = keys

        self.value_widget = TextListSubWidget(
            input_data, values, parent_keys, self
        )
        self.value_widget.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.value_widget.value_changed.connect(self._on_value_change)

        # self.value_widget.se
        self.key = input_data["key"]
        layout.addWidget(self.value_widget)
        self.setLayout(layout)

        self.origin_value = self.item_value()

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def _on_value_change(self, value=None):
        self.is_modified = self.item_value() != self.origin_value
        if self.is_group and self.is_overidable:
            self.is_overriden = True

        self._update_style()

        self.value_changed.emit()

    def set_value(self, value, origin_value=False):
        self.value_widget.set_value(value)
        if origin_value:
            self.origin_value = self.item_value()
            self._on_value_change()

    def reset_value(self):
        self.set_value(self.origin_value)

    def clear_value(self):
        self.set_value([])

    def _update_style(self):
        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        return self.value_widget.config_value()

    def config_value(self):
        return {self.key: self.item_value()}


class DictExpandWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

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

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        self.any_parent_is_group = any_parent_is_group

        self.is_modified = False
        self._is_overriden = False
        self.is_group = is_group

        super(DictExpandWidget, self).__init__(parent)
        self.setObjectName("DictExpandWidget")
        top_part = ClickableWidget(parent=self)

        button_size = QtCore.QSize(5, 5)
        button_toggle = QtWidgets.QToolButton(parent=top_part)
        button_toggle.setProperty("btn-type", "expand-toggle")
        button_toggle.setIconSize(button_size)
        button_toggle.setArrowType(QtCore.Qt.RightArrow)
        button_toggle.setCheckable(True)
        button_toggle.setChecked(False)

        label = input_data["label"]
        button_toggle_text = QtWidgets.QLabel(label, parent=top_part)
        button_toggle_text.setObjectName("ExpandLabel")

        layout = QtWidgets.QHBoxLayout(top_part)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(button_toggle)
        layout.addWidget(button_toggle_text)
        top_part.setLayout(layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(9, 9, 9, 9)

        content_widget = QtWidgets.QWidget(self)
        content_widget.setVisible(False)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)

        main_layout.addWidget(top_part)
        main_layout.addWidget(content_widget)
        self.setLayout(main_layout)

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        self.top_part = top_part
        self.button_toggle = button_toggle
        self.button_toggle_text = button_toggle_text

        self.content_widget = content_widget
        self.content_layout = content_layout

        self.top_part.clicked.connect(self._top_part_clicked)
        self.button_toggle.clicked.connect(self.toggle_content)

        self.input_fields = []

        self.key = input_data["key"]
        keys = list(parent_keys)
        keys.append(self.key)
        self.keys = keys

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data, values)

    def _top_part_clicked(self):
        self.toggle_content(not self.button_toggle.isChecked())

    def toggle_content(self, *args):
        if len(args) > 0:
            checked = args[0]
        else:
            checked = self.button_toggle.isChecked()
        arrow_type = QtCore.Qt.RightArrow
        if checked:
            arrow_type = QtCore.Qt.DownArrow
        self.button_toggle.setChecked(checked)
        self.button_toggle.setArrowType(arrow_type)
        self.content_widget.setVisible(checked)
        self.parent().updateGeometry()

    def resizeEvent(self, event):
        super(DictExpandWidget, self).resizeEvent(event)
        self.content_widget.updateGeometry()

    @property
    def is_overriden(self):
        if self._is_overriden:
            return self._is_overriden
        return self._parent.is_overriden

    def _on_value_change(self, value=None):
        if self.is_group:
            self._is_overriden = True

        self.value_changed.emit()

        self._update_style()

    def _update_style(self):
        child_modified = self.child_modified
        child_overriden = self.child_overriden

        if child_modified and child_overriden:
            widget_state = "child-overriden-modified"
        elif child_modified:
            widget_state = "child-modified"
        elif child_overriden:
            widget_state = "child-overriden"
        else:
            widget_state = ""

        self.setProperty("state", widget_state)
        self.style().polish(self)

        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

        self.button_toggle_text.setProperty("state", state)
        self.button_toggle_text.style().polish(self.button_toggle_text)

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

    def config_value(self):
        return {self.key: self.item_value()}

    @property
    def is_overidable(self):
        return self._parent.is_overidable

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


class DictInvisible(QtWidgets.QWidget, PypeConfigurationWidget):
    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        self.any_parent_is_group = any_parent_is_group

        self.is_modified = False
        self.is_overriden = False
        self.is_group = is_group

        super(DictInvisible, self).__init__(parent)
        self.setObjectName("DictInvisible")

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.input_fields = []

        if "key" not in input_data:
            print(json.dumps(input_data, indent=4))

        self.key = input_data["key"]
        self.keys = list(parent_keys)
        self.keys.append(self.key)

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data, values)

    @property
    def is_overidable(self):
        return self._parent.is_overidable

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

    def config_value(self):
        return {self.key: self.item_value()}

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        if item_type == "schema":
            for _schema in child_configuration["children"]:
                children = config.gui_schema(_schema)
                self.add_children_gui(children, values)
            return

        klass = TypeToKlass.types.get(item_type)
        item = klass(
            child_configuration, values, self.keys, self
        )
        self.layout().addWidget(item)

        self.input_fields.append(item)
        return item


class DictFormWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    def __init__(
        self, input_data, values, parent_keys, parent, label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self.any_parent_is_group = any_parent_is_group

        self.is_modified = False
        self.is_overriden = False
        self.is_group = False

        super(DictFormWidget, self).__init__(parent)

        self.input_fields = {}
        self.content_layout = QtWidgets.QFormLayout(self)

        self.keys = list(parent_keys)

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data, values)

    def _on_value_change(self):
        self.value_changed.emit()

    def item_value(self):
        output = {}
        for input_field in self.input_fields.values():
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    @property
    def child_modified(self):
        for input_field in self.input_fields.values():
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
    def is_overidable(self):
        return self._parent.is_overidable

    def config_value(self):
        return self.item_value()

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        key = child_configuration["key"]
        # Pop label to not be set in child
        label = child_configuration["label"]

        klass = TypeToKlass.types.get(item_type)

        label_widget = QtWidgets.QLabel(label)

        item = klass(
            child_configuration, values, self.keys, self, label_widget
        )
        item.value_changed.connect(self._on_value_change)
        self.content_layout.addRow(label_widget, item)
        self.input_fields[key] = item
        return item


class ModifiableDictItem(QtWidgets.QWidget, PypeConfigurationWidget):
    _btn_size = 20
    value_changed = QtCore.Signal()

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

        self.origin_key = self._key()
        self.origin_value = self.value_input.item_value()

        self.is_single = False

    def _key(self):
        return self.key_input.text()

    def _on_value_change(self):
        self._update_style()
        self.value_changed.emit()

    @property
    def is_group(self):
        return self._parent.is_group

    @property
    def any_parent_is_group(self):
        return self._parent.any_parent_is_group

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def is_key_modified(self):
        return self._key() != self.origin_key

    def is_value_modified(self):
        return self.value_input.is_modified

    @property
    def is_modified(self):
        return self.is_value_modified() or self.is_key_modified()

    def _update_style(self):
        # if self._is_overidable and self.is_overriden:
        #     if is_modified:
        #         state = "overriden-modified"
        #     else:
        #         state = "overriden"
        if self.is_key_modified():
            state = "modified"
        else:
            state = "original"

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


class ModifiableDictSubWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    value_changed = QtCore.Signal()

    def __init__(self, input_data, values, parent_keys, parent):
        self._parent = parent

        super(ModifiableDictSubWidget, self).__init__(parent)
        self.setObjectName("ModifiableDictSubWidget")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
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

        self.origin_value = self.config_value()

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    @property
    def is_group(self):
        return self._parent.is_group

    @property
    def any_parent_is_group(self):
        return self._parent.any_parent_is_group

    def _on_value_change(self):
        self.value_changed.emit()

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
            item_widget.origin_key = key
            item_widget.key_input.setText(key)
            item_widget.value_input.set_value(value, origin_value=True)
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


class ModifiableDict(ExpandingWidget, PypeConfigurationWidget):
    def __init__(
        self, input_data, values, parent_keys, parent,
        label_widget=None
    ):
        self._parent = parent

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        is_group = input_data.get("is_group", False)
        if is_group and any_parent_is_group:
            raise SchemeGroupHierarchyBug()

        self.any_parent_is_group = any_parent_is_group

        self.is_modified = False
        self.child_modified = False
        self.is_overriden = False
        self.is_group = is_group

        super(ModifiableDict, self).__init__(input_data["label"], parent)
        self.setObjectName("ModifiableDict")

        self.value_widget = ModifiableDictSubWidget(
            input_data, values, parent_keys, self
        )
        self.value_widget.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.value_widget.value_changed.connect(self._on_value_change)

        self.set_content_widget(self.value_widget)

        self.key = input_data["key"]

        self.origin_value = self.item_value()

    def _on_value_change(self, value=None):
        self.child_modified = self.item_value() != self.origin_value
        if self.is_group:
            self.is_overriden = True

        self._update_style()

    @property
    def child_overriden(self):
        return self.is_overriden

    @property
    def is_overidable(self):
        return self._parent.is_overidable

    def _update_style(self):
        child_modified = self.child_modified
        child_overriden = self.child_overriden

        if child_modified and child_overriden:
            widget_state = "child-overriden-modified"
        elif child_modified:
            widget_state = "child-modified"
        elif child_overriden:
            widget_state = "child-overriden"
        else:
            widget_state = ""

        self.setProperty("state", widget_state)
        self.style().polish(self)

        if self.is_overidable and self.is_overriden:
            if self.is_modified:
                state = "overriden-modified"
            else:
                state = "overriden"
        elif self.is_modified:
            state = "modified"
        else:
            state = "original"

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        return self.value_widget.config_value()

    def config_value(self):
        return {self.key: self.item_value()}


TypeToKlass.types["boolean"] = BooleanWidget
TypeToKlass.types["text-singleline"] = TextSingleLineWidget
TypeToKlass.types["text-multiline"] = TextMultiLineWidget
TypeToKlass.types["int"] = IntegerWidget
TypeToKlass.types["float"] = FloatWidget
TypeToKlass.types["dict-expanding"] = DictExpandWidget
TypeToKlass.types["dict-form"] = DictFormWidget
TypeToKlass.types["dict-invisible"] = DictInvisible
TypeToKlass.types["dict-modifiable"] = ModifiableDict
TypeToKlass.types["list-text"] = TextListWidget
