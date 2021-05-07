from Qt import QtWidgets, QtCore

from .multiselection_combobox import MultiSelectionComboBox


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
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)

        value = index.data(QtCore.Qt.EditRole)
        if value is not None:
            try:
                if isinstance(value, str):
                    value = float(value)
                editor.setValue(value)

            except Exception:
                print("Couldn't set invalid value \"{}\"".format(str(value)))

        return editor

    # def updateEditorGeometry(self, editor, options, index):
    #     print(editor)
    #     return super().updateEditorGeometry(editor, options, index)


class StringDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        value = index.data(QtCore.Qt.EditRole)
        if value is not None:
            editor.setText(str(value))
        return editor


class TypeDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, project_doc_cache, *args, **kwargs):
        self._project_doc_cache = project_doc_cache
        super(TypeDelegate, self).__init__(*args, **kwargs)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        if not self._project_doc_cache.project_doc:
            return editor

        task_type_defs = self._project_doc_cache.project_doc["config"]["tasks"]
        editor.addItems(list(task_type_defs.keys()))

        return editor


class ToolsDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, tools_cache, *args, **kwargs):
        self._tools_cache = tools_cache
        super(ToolsDelegate, self).__init__(*args, **kwargs)

    def createEditor(self, parent, option, index):
        editor = MultiSelectionComboBox(parent)
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
