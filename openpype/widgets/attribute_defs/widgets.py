import uuid

from Qt import QtWidgets, QtCore

from openpype.lib.attribute_definitions import (
    AbtractAttrDef,
    UnknownDef,
    NumberDef,
    TextDef,
    EnumDef,
    BoolDef,
    FileDef,
    UISeparatorDef,
    UILabelDef
)
from openpype.widgets.nice_checkbox import NiceCheckbox

from .files_widget import FilesWidget


def create_widget_for_attr_def(attr_def, parent=None):
    if not isinstance(attr_def, AbtractAttrDef):
        raise TypeError("Unexpected type \"{}\" expected \"{}\"".format(
            str(type(attr_def)), AbtractAttrDef
        ))

    if isinstance(attr_def, NumberDef):
        return NumberAttrWidget(attr_def, parent)

    if isinstance(attr_def, TextDef):
        return TextAttrWidget(attr_def, parent)

    if isinstance(attr_def, EnumDef):
        return EnumAttrWidget(attr_def, parent)

    if isinstance(attr_def, BoolDef):
        return BoolAttrWidget(attr_def, parent)

    if isinstance(attr_def, UnknownDef):
        return UnknownAttrWidget(attr_def, parent)

    if isinstance(attr_def, FileDef):
        return FileAttrWidget(attr_def, parent)

    if isinstance(attr_def, UISeparatorDef):
        return SeparatorAttrWidget(attr_def, parent)

    if isinstance(attr_def, UILabelDef):
        return LabelAttrWidget(attr_def, parent)

    raise ValueError("Unknown attribute definition \"{}\"".format(
        str(type(attr_def))
    ))


class _BaseAttrDefWidget(QtWidgets.QWidget):
    # Type 'object' may not work with older PySide versions
    value_changed = QtCore.Signal(object, uuid.UUID)

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
            input_widget = QtWidgets.QDoubleSpinBox(self)
            input_widget.setDecimals(decimals)
        else:
            input_widget = QtWidgets.QSpinBox(self)

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
    def _ui_init(self):
        input_widget = QtWidgets.QComboBox(self)
        combo_delegate = QtWidgets.QStyledItemDelegate(input_widget)
        input_widget.setItemDelegate(combo_delegate)

        if self.attr_def.tooltip:
            input_widget.setToolTip(self.attr_def.tooltip)

        items = self.attr_def.items
        for key, label in items.items():
            input_widget.addItem(label, key)

        idx = input_widget.findData(self.attr_def.default)
        if idx >= 0:
            input_widget.setCurrentIndex(idx)

        input_widget.currentIndexChanged.connect(self._on_value_change)

        self._combo_delegate = combo_delegate
        self._input_widget = input_widget

        self.main_layout.addWidget(input_widget, 0)

    def _on_value_change(self):
        new_value = self.current_value()
        self.value_changed.emit(new_value, self.attr_def.id)

    def current_value(self):
        idx = self._input_widget.currentIndex()
        return self._input_widget.itemData(idx)

    def set_value(self, value, multivalue=False):
        if not multivalue:
            idx = self._input_widget.findData(value)
            cur_idx = self._input_widget.currentIndex()
            if idx != cur_idx and idx >= 0:
                self._input_widget.setCurrentIndex(idx)

        else:
            self._input_widget.lineEdit().setText("Multiselection")


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


class FileAttrWidget(_BaseAttrDefWidget):
    def _ui_init(self):
        input_widget = FilesWidget(
             self.attr_def.single_item, self.attr_def.sequence_extensions, self
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
