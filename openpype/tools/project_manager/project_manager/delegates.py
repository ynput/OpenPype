from Qt import QtWidgets, QtCore

from .widgets import (
    NameTextEdit,
    FilterComboBox
)
from .multiselection_combobox import MultiSelectionComboBox


class ResizeEditorDelegate(QtWidgets.QStyledItemDelegate):
    @staticmethod
    def _q_smart_min_size(editor):
        min_size_hint = editor.minimumSizeHint()
        size_policy = editor.sizePolicy()
        width = 0
        height = 0
        if size_policy.horizontalPolicy() != QtWidgets.QSizePolicy.Ignored:
            if (
                size_policy.horizontalPolicy()
                & QtWidgets.QSizePolicy.ShrinkFlag
            ):
                width = min_size_hint.width()
            else:
                width = max(
                    editor.sizeHint().width(),
                    min_size_hint.width()
                )

        if size_policy.verticalPolicy() != QtWidgets.QSizePolicy.Ignored:
            if size_policy.verticalPolicy() & QtWidgets.QSizePolicy.ShrinkFlag:
                height = min_size_hint.height()
            else:
                height = max(
                    editor.sizeHint().height(),
                    min_size_hint.height()
                )

        output = QtCore.QSize(width, height).boundedTo(editor.maximumSize())
        min_size = editor.minimumSize()
        if min_size.width() > 0:
            output.setWidth(min_size.width())
        if min_size.height() > 0:
            output.setHeight(min_size.height())

        return output.expandedTo(QtCore.QSize(0, 0))

    def updateEditorGeometry(self, editor, option, index):
        self.initStyleOption(option, index)

        option.showDecorationSelected = editor.style().styleHint(
            QtWidgets.QStyle.SH_ItemView_ShowDecorationSelected, None, editor
        )

        widget = option.widget

        style = widget.style() if widget else QtWidgets.QApplication.style()
        geo = style.subElementRect(
            QtWidgets.QStyle.SE_ItemViewItemText, option, widget
        )
        delta = self._q_smart_min_size(editor).width() - geo.width()
        if delta > 0:
            if editor.layoutDirection() == QtCore.Qt.RightToLeft:
                geo.adjust(-delta, 0, 0, 0)
            else:
                geo.adjust(0, 0, delta, 0)
        editor.setGeometry(geo)


class NumberDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, minimum, maximum, decimals, *args, **kwargs):
        super(NumberDelegate, self).__init__(*args, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals

    def createEditor(self, parent, option, index):
        if self.decimals > 0:
            editor = QtWidgets.QDoubleSpinBox(parent)
        else:
            editor = QtWidgets.QSpinBox(parent)

        editor.setObjectName("NumberEditor")
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setButtonSymbols(QtWidgets.QSpinBox.NoButtons)

        value = index.data(QtCore.Qt.EditRole)
        if value is not None:
            try:
                if isinstance(value, str):
                    value = float(value)
                editor.setValue(value)

            except Exception:
                print("Couldn't set invalid value \"{}\"".format(str(value)))

        return editor


class NameDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = NameTextEdit(parent)
        editor.setObjectName("NameEditor")
        value = index.data(QtCore.Qt.EditRole)
        if value is not None:
            editor.setText(str(value))
        return editor


class TypeDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, project_doc_cache, *args, **kwargs):
        self._project_doc_cache = project_doc_cache
        super(TypeDelegate, self).__init__(*args, **kwargs)

    def createEditor(self, parent, option, index):
        editor = FilterComboBox(parent)
        editor.setObjectName("TypeEditor")
        editor.style().polish(editor)
        if not self._project_doc_cache.project_doc:
            return editor

        task_type_defs = self._project_doc_cache.project_doc["config"]["tasks"]
        editor.addItems(list(task_type_defs.keys()))

        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.EditRole)
        index = editor.findText(value)
        if index >= 0:
            editor.setCurrentIndex(index)


class ToolsDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, tools_cache, *args, **kwargs):
        self._tools_cache = tools_cache
        super(ToolsDelegate, self).__init__(*args, **kwargs)

    def createEditor(self, parent, option, index):
        editor = MultiSelectionComboBox(parent)
        editor.setObjectName("ToolEditor")
        if not self._tools_cache.tools_data:
            return editor

        for key, label in self._tools_cache.tools_data:
            editor.addItem(label, key)

        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.EditRole)
        editor.set_value(value)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), QtCore.Qt.EditRole)
