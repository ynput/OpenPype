from Qt import QtWidgets, QtCore

from .widgets import (
    NameTextEdit,
    FilterComboBox,
    SpinBoxScrollFixed,
    DoubleSpinBoxScrollFixed
)
from .multiselection_combobox import MultiSelectionComboBox


class ResizeEditorDelegate(QtWidgets.QStyledItemDelegate):
    """Implementation of private method from QStyledItemDelegate.

    Force editor to resize into item size.
    """
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
    """Delegate for number attributes.

    Editor correspond passed arguments.

    Args:
        minimum(int, float): Minimum possible value.
        maximum(int, float): Maximum possible value.
        decimals(int): How many decimal points can be used. Float will be used
            as value if is higher than 0.
    """
    def __init__(self, minimum, maximum, decimals, *args, **kwargs):
        super(NumberDelegate, self).__init__(*args, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals

    def createEditor(self, parent, option, index):
        if self.decimals > 0:
            editor = DoubleSpinBoxScrollFixed(parent)
        else:
            editor = SpinBoxScrollFixed(parent)

        editor.setObjectName("NumberEditor")
        # Set min/max
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        # Hide spinbox buttons
        editor.setButtonSymbols(QtWidgets.QSpinBox.NoButtons)

        # Try to set value from item
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
    """Specific delegate for "name" key."""

    def createEditor(self, parent, option, index):
        editor = NameTextEdit(parent)
        editor.setObjectName("NameEditor")
        value = index.data(QtCore.Qt.EditRole)
        if value is not None:
            editor.setText(str(value))
        return editor


class TypeDelegate(QtWidgets.QStyledItemDelegate):
    """Specific delegate for "type" key.

    It is expected that will be used only for TaskItem which has modifiable
    type. Type values are defined with cached project document.

    Args:
        project_doc_cache(ProjectDocCache): Project cache shared across all
            delegates (kind of a struct pointer).
    """

    def __init__(self, project_doc_cache, *args, **kwargs):
        self._project_doc_cache = project_doc_cache
        super(TypeDelegate, self).__init__(*args, **kwargs)

    def createEditor(self, parent, option, index):
        """Editor is using filtrable combobox.

        Editor should not be possible to create new items or set values that
        are not in this method.
        """
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

    def setModelData(self, editor, model, index):
        editor.value_cleanup()
        super(TypeDelegate, self).setModelData(editor, model, index)


class ToolsDelegate(QtWidgets.QStyledItemDelegate):
    """Specific delegate for "tools_env" key.

    Expected that editor will be used only on AssetItem which is the only item
    that can have `tools_env` (except project).

    Delegate requires tools cache which is shared across all ToolsDelegate
    objects.

    Args:
        tools_cache (ToolsCache): Possible values of tools.
    """

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
