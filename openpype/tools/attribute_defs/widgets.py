import collections
import copy

from qtpy import QtWidgets, QtCore

from openpype.lib.attribute_definitions import (
    AbstractAttrDef,
    UnknownDef,
    HiddenDef,
    NumberDef,
    TextDef,
    EnumDef,
    BoolDef,
    EnumObjectDef,
    FileDef,
    UIDef,
    UISeparatorDef,
    UILabelDef
)
from openpype.tools.utils import (
    CustomTextComboBox,
    FocusSpinBox,
    FocusDoubleSpinBox,
)
from openpype.widgets.nice_checkbox import NiceCheckbox

from .files_widget import FilesWidget


def create_widget_for_attr_def(attr_def, parent=None):
    widget = _create_widget_for_attr_def(attr_def, parent)
    if attr_def.hidden:
        widget.setVisible(False)

    if attr_def.disabled:
        widget.setEnabled(False)
    return widget


def _create_widget_for_attr_def(attr_def, parent=None):
    if not isinstance(attr_def, AbstractAttrDef):
        raise TypeError("Unexpected type \"{}\" expected \"{}\"".format(
            str(type(attr_def)), AbstractAttrDef
        ))

    if isinstance(attr_def, NumberDef):
        return NumberAttrWidget(attr_def, parent)

    if isinstance(attr_def, TextDef):
        return TextAttrWidget(attr_def, parent)

    if isinstance(attr_def, EnumDef):
        return EnumAttrWidget(attr_def, parent)

    if isinstance(attr_def, BoolDef):
        return BoolAttrWidget(attr_def, parent)

    if isinstance(attr_def, EnumObjectDef):
        return EnumObjectAttrWidget(attr_def, parent)

    if isinstance(attr_def, UnknownDef):
        return UnknownAttrWidget(attr_def, parent)

    if isinstance(attr_def, HiddenDef):
        return HiddenAttrWidget(attr_def, parent)

    if isinstance(attr_def, FileDef):
        return FileAttrWidget(attr_def, parent)

    if isinstance(attr_def, UISeparatorDef):
        return SeparatorAttrWidget(attr_def, parent)

    if isinstance(attr_def, UILabelDef):
        return LabelAttrWidget(attr_def, parent)

    raise ValueError("Unknown attribute definition \"{}\"".format(
        str(type(attr_def))
    ))


class AttributeDefinitionsWidget(QtWidgets.QWidget):
    """Create widgets for attribute definitions in grid layout.

    Widget creates input widgets for passed attribute definitions.

    Widget can't handle multiselection values.
    """

    def __init__(self, attr_defs=None, parent=None):
        super(AttributeDefinitionsWidget, self).__init__(parent)

        self._widgets = []
        self._current_keys = set()

        self.set_attr_defs(attr_defs)

    def clear_attr_defs(self):
        """Remove all existing widgets and reset layout if needed."""
        self._widgets = []
        self._current_keys = set()

        layout = self.layout()
        if layout is not None:
            if layout.count() == 0:
                return

            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setVisible(False)
                    widget.deleteLater()

            layout.deleteLater()

        new_layout = QtWidgets.QGridLayout()
        new_layout.setColumnStretch(0, 0)
        new_layout.setColumnStretch(1, 1)
        self.setLayout(new_layout)

    def set_attr_defs(self, attr_defs):
        """Replace current attribute definitions with passed."""
        self.clear_attr_defs()
        if attr_defs:
            self.add_attr_defs(attr_defs)

    def add_attr_defs(self, attr_defs):
        """Add attribute definitions to current."""
        layout = self.layout()

        row = 0
        for attr_def in attr_defs:
            if not isinstance(attr_def, UIDef):
                if attr_def.key in self._current_keys:
                    raise KeyError(
                        "Duplicated key \"{}\"".format(attr_def.key))

                self._current_keys.add(attr_def.key)
            widget = create_widget_for_attr_def(attr_def, self)
            self._widgets.append(widget)

            if attr_def.hidden:
                continue

            expand_cols = 2
            if attr_def.is_value_def and attr_def.is_label_horizontal:
                expand_cols = 1

            col_num = 2 - expand_cols

            if attr_def.label:
                label_widget = QtWidgets.QLabel(attr_def.label, self)
                tooltip = attr_def.tooltip
                if tooltip:
                    label_widget.setToolTip(tooltip)
                layout.addWidget(
                    label_widget, row, 0, 1, expand_cols
                )
                if not attr_def.is_label_horizontal:
                    row += 1

            layout.addWidget(
                widget, row, col_num, 1, expand_cols
            )
            row += 1

    def set_value(self, value, multivalue=False):
        new_value = copy.deepcopy(value)
        for widget in self._widgets:
            attr_def = widget.attr_def
            if attr_def.key not in new_value:
                continue

            widget_value = new_value[attr_def.key]
            if widget_value is None:
                widget_value = copy.deepcopy(attr_def.default)
            widget.set_value(widget_value, multivalue)

    def current_value(self):
        output = {}
        for widget in self._widgets:
            attr_def = widget.attr_def
            if not isinstance(attr_def, UIDef):
                output[attr_def.key] = widget.current_value()

        return output


class _BaseAttrDefWidget(QtWidgets.QWidget):
    # Type 'object' may not work with older PySide versions
    value_changed = QtCore.Signal(object, str)

    def __init__(self, attr_def, parent):
        super(_BaseAttrDefWidget, self).__init__(parent)

        self.attr_def = attr_def

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_layout = main_layout

        self._ui_init()

    def _ui_init(self):
        raise NotImplementedError(
            "Method '_ui_init' is not implemented. {}".format(
                self.__class__.__name__
            )
        )

    def current_value(self):
        raise NotImplementedError(
            "Method 'current_value' is not implemented. {}".format(
                self.__class__.__name__
            )
        )

    def set_value(self, value, multivalue=False):
        raise NotImplementedError(
            "Method 'set_value' is not implemented. {}".format(
                self.__class__.__name__
            )
        )


class SeparatorAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        input_widget = QtWidgets.QWidget(self)
        input_widget.setObjectName("Separator")
        input_widget.setMinimumHeight(2)
        input_widget.setMaximumHeight(2)

        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)


class LabelAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        input_widget = QtWidgets.QLabel(self)
        label = self.attr_def.label
        if label:
            input_widget.setText(str(label))

        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)


class NumberAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        decimals = self.attr_def.decimals
        if decimals > 0:
            input_widget = FocusDoubleSpinBox(self)
            input_widget.setDecimals(decimals)
        else:
            input_widget = FocusSpinBox(self)

        if self.attr_def.tooltip:
            input_widget.setToolTip(self.attr_def.tooltip)

        input_widget.setMinimum(self.attr_def.minimum)
        input_widget.setMaximum(self.attr_def.maximum)
        input_widget.setValue(self.attr_def.default)

        input_widget.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        input_widget.valueChanged.connect(self._on_value_change)

        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)

    def _on_value_change(self, new_value):
        self.value_changed.emit(new_value, self.attr_def.id)

    def current_value(self):
        return self._input_widget.value()

    def set_value(self, value, multivalue=False):
        if multivalue:
            set_value = set(value)
            if None in set_value:
                set_value.remove(None)
                set_value.add(self.attr_def.default)

            if len(set_value) > 1:
                self._input_widget.setSpecialValueText("Multiselection")
                return
            value = tuple(set_value)[0]

        if self.current_value != value:
            self._input_widget.setValue(value)


class TextAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        # TODO Solve how to handle regex
        # self.attr_def.regex

        self.multiline = self.attr_def.multiline
        if self.multiline:
            input_widget = QtWidgets.QPlainTextEdit(self)
        else:
            input_widget = QtWidgets.QLineEdit(self)

        if (
            self.attr_def.placeholder
            and hasattr(input_widget, "setPlaceholderText")
        ):
            input_widget.setPlaceholderText(self.attr_def.placeholder)

        if self.attr_def.tooltip:
            input_widget.setToolTip(self.attr_def.tooltip)

        if self.attr_def.default:
            if self.multiline:
                input_widget.setPlainText(self.attr_def.default)
            else:
                input_widget.setText(self.attr_def.default)

        input_widget.textChanged.connect(self._on_value_change)

        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)

    def _on_value_change(self):
        if self.multiline:
            new_value = self._input_widget.toPlainText()
        else:
            new_value = self._input_widget.text()
        self.value_changed.emit(new_value, self.attr_def.id)

    def current_value(self):
        if self.multiline:
            return self._input_widget.toPlainText()
        return self._input_widget.text()

    def set_value(self, value, multivalue=False):
        if multivalue:
            set_value = set(value)
            if None in set_value:
                set_value.remove(None)
                set_value.add(self.attr_def.default)

            if len(set_value) == 1:
                value = tuple(set_value)[0]
            else:
                value = "< Multiselection >"

        if value != self.current_value():
            if self.multiline:
                self._input_widget.setPlainText(value)
            else:
                self._input_widget.setText(value)


class BoolAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        input_widget = NiceCheckbox(parent=self)
        input_widget.setChecked(self.attr_def.default)

        if self.attr_def.tooltip:
            input_widget.setToolTip(self.attr_def.tooltip)

        input_widget.stateChanged.connect(self._on_value_change)

        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)
        self.main_layout.addStretch(1)

    def _on_value_change(self):
        new_value = self._input_widget.isChecked()
        self.value_changed.emit(new_value, self.attr_def.id)

    def current_value(self):
        return self._input_widget.isChecked()

    def set_value(self, value, multivalue=False):
        if multivalue:
            set_value = set(value)
            if None in set_value:
                set_value.remove(None)
                set_value.add(self.attr_def.default)

            if len(set_value) > 1:
                self._input_widget.setCheckState(QtCore.Qt.PartiallyChecked)
                return
            value = tuple(set_value)[0]

        if value != self.current_value():
            self._input_widget.setChecked(value)


class EnumAttrWidget(_BaseAttrDefWidget):
    def __init__(self, *args, **kwargs):
        self._multivalue = False
        super(EnumAttrWidget, self).__init__(*args, **kwargs)

    def _ui_init(self):
        input_widget = CustomTextComboBox(self)
        combo_delegate = QtWidgets.QStyledItemDelegate(input_widget)
        input_widget.setItemDelegate(combo_delegate)

        if self.attr_def.tooltip:
            input_widget.setToolTip(self.attr_def.tooltip)

        for item in self.attr_def.items:
            input_widget.addItem(item["label"], item["value"])

        idx = input_widget.findData(self.attr_def.default)
        if idx >= 0:
            input_widget.setCurrentIndex(idx)

        input_widget.currentIndexChanged.connect(self._on_value_change)

        self._combo_delegate = combo_delegate
        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)

    def _on_value_change(self):
        new_value = self.current_value()
        if self._multivalue:
            self._multivalue = False
            self._input_widget.set_custom_text(None)
        self.value_changed.emit(new_value, self.attr_def.id)

    def current_value(self):
        idx = self._input_widget.currentIndex()
        return self._input_widget.itemData(idx)

    def set_value(self, value, multivalue=False):
        if multivalue:
            set_value = set(value)
            if len(set_value) == 1:
                multivalue = False
                value = tuple(set_value)[0]

        if not multivalue:
            idx = self._input_widget.findData(value)
            cur_idx = self._input_widget.currentIndex()
            if idx != cur_idx and idx >= 0:
                self._input_widget.setCurrentIndex(idx)

        custom_text = None
        if multivalue:
            custom_text = "< Multiselection >"
        self._input_widget.set_custom_text(custom_text)
        self._multivalue = multivalue


class UnknownAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        input_widget = QtWidgets.QLabel(self)
        self._value = self.attr_def.default
        input_widget.setText(str(self._value))

        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)

    def current_value(self):
        raise ValueError(
            "{} can't hold real value.".format(self.__class__.__name__)
        )

    def set_value(self, value, multivalue=False):
        if multivalue:
            set_value = set(value)
            if len(set_value) == 1:
                value = tuple(set_value)[0]
            else:
                value = "< Multiselection >"

        str_value = str(value)
        if str_value != self._value:
            self._value = str_value
            self._input_widget.setText(str_value)


class HiddenAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        self.setVisible(False)
        self._value = None
        self._multivalue = False

    def setVisible(self, visible):
        if visible:
            visible = False
        super(HiddenAttrWidget, self).setVisible(visible)

    def current_value(self):
        if self._multivalue:
            raise ValueError("{} can't output for multivalue.".format(
                self.__class__.__name__
            ))
        return self._value

    def set_value(self, value, multivalue=False):
        self._value = copy.deepcopy(value)
        self._multivalue = multivalue


class FileAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        input_widget = FilesWidget(
            self.attr_def.single_item,
            self.attr_def.allow_sequences,
            self.attr_def.extensions_label,
            self
        )

        if self.attr_def.tooltip:
            input_widget.setToolTip(self.attr_def.tooltip)

        input_widget.set_filters(
            self.attr_def.folders, self.attr_def.extensions
        )

        input_widget.value_changed.connect(self._on_value_change)

        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)

    def _on_value_change(self):
        new_value = self.current_value()
        self.value_changed.emit(new_value, self.attr_def.id)

    def current_value(self):
        return self._input_widget.current_value()

    def set_value(self, value, multivalue=False):
        self._input_widget.set_value(value, multivalue)


class EnumObjectAttrWidget(_BaseAttrDefWidget):
    def __init__(self, *args, **kwargs):
        self._multivalue = False
        super(EnumObjectAttrWidget, self).__init__(*args, **kwargs)

    def _ui_init(self):
        content_widget = QtWidgets.QWidget(self)

        enum_wrap_widget = QtWidgets.QWidget(content_widget)
        enum_widget = CustomTextComboBox(enum_wrap_widget)
        combo_delegate = QtWidgets.QStyledItemDelegate(enum_widget)
        enum_widget.setItemDelegate(combo_delegate)

        if self.attr_def.tooltip:
            enum_widget.setToolTip(self.attr_def.tooltip)

        values = []
        for item in self.attr_def.enum_items:
            enum_widget.addItem(item["label"], item["value"])
            values.append(item["value"])

        idx = enum_widget.findData(self.attr_def.enum_default)
        if idx >= 0:
            enum_widget.setCurrentIndex(idx)

        enum_wrap_layout = QtWidgets.QHBoxLayout(enum_wrap_widget)
        enum_wrap_layout.setContentsMargins(0, 0, 0, 0)
        if self.attr_def.enum_label:
            enum_label = QtWidgets.QLabel(self.attr_def.enum_label)
            enum_wrap_layout.addWidget(enum_label)
        enum_wrap_layout.addWidget(enum_widget, 1)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(enum_wrap_widget)
        subwidgets_by_value = {}
        for value in values:
            children = self.attr_def.children_by_enum[value]
            if not children:
                subwidgets_by_value[value] = None
                continue
            widget = AttributeDefinitionsWidget(children, content_widget)
            widget.setVisible(value == self.attr_def.enum_default)
            widget.layout().setContentsMargins(0, 0, 0, 0)
            subwidgets_by_value[value] = widget
            content_layout.addWidget(widget)

        enum_widget.currentIndexChanged.connect(self._on_enum_value_change)

        self._combo_delegate = combo_delegate
        self._enum_widget = enum_widget
        self._subwidgets_by_value = subwidgets_by_value

        self.main_layout.addWidget(content_widget, 0)

    def _on_enum_value_change(self):
        new_enum_value = self.current_enum_value()
        if self._multivalue:
            self._multivalue = False
            self._enum_widget.set_custom_text(None)

        for enum_value, widget in self._subwidgets_by_value.items():
            if widget is not None:
                widget.setVisible(enum_value == new_enum_value)

        self.value_changed.emit(self.current_value(), self.attr_def.id)

    def current_enum_value(self):
        idx = self._enum_widget.currentIndex()
        return self._enum_widget.itemData(idx)

    def current_value(self):
        enum_value = self.current_enum_value()
        output = {self.attr_def.enum_key: enum_value}
        subwidget = self._subwidgets_by_value[enum_value]
        if subwidget:
            output.update(subwidget.current_value())

        return output

    def set_value(self, value, multivalue=False):
        orig_multivalue = multivalue
        if not multivalue:
            enum_value = value[self.attr_def.enum_key]
            values_by_enum_values = {enum_value: value}
            value = enum_value
        else:
            values_by_enum_values = {}
            for item in value:
                enum_value = item[self.attr_def.enum_key]
                values_by_enum_values.setdefault(
                    enum_value, collections.defaultdict(list)
                )
                _values = values_by_enum_values[enum_value]
                for k, v in item.items():
                    _values[k].append(v)

            enum_values = set(values_by_enum_values.keys())
            if len(enum_values) == 1:
                multivalue = False
                value = next(iter(enum_values))

        if not multivalue:
            idx = self._enum_widget.findData(value)
            cur_idx = self._enum_widget.currentIndex()
            if idx != cur_idx and idx >= 0:
                self._enum_widget.setCurrentIndex(idx)

        if multivalue:
            custom_text = "< Multiselection >"
            for enum_value, widget in self._subwidgets_by_value.items():
                if widget is None:
                    continue
                widget.setVisible(False)
                if enum_value in values_by_enum_values:
                    widget.set_value(
                        values_by_enum_values[enum_value], orig_multivalue
                    )
        else:
            custom_text = None
            for enum_value, widget in self._subwidgets_by_value.items():
                if widget is None:
                    continue
                widget.setVisible(value == enum_value)
                if enum_value in values_by_enum_values:
                    widget.set_value(
                        values_by_enum_values[enum_value], orig_multivalue
                    )

        self._enum_widget.set_custom_text(custom_text)
        self._multivalue = multivalue
