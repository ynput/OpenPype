from Qt import QtWidgets, QtCore


class NumberDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QSpinBox(parent)
        editor.setMaximum(999999)
        editor.setMinimum(0)
        value = index.data(QtCore.Qt.DisplayRole)
        if value is not None:
            editor.setValue(value)
        return editor

    # def updateEditorGeometry(self, editor, options, index):
    #     print(editor)
    #     return super().updateEditorGeometry(editor, options, index)


class StringDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        value = index.data(QtCore.Qt.DisplayRole)
        if value is not None:
            editor.setText(str(value))
        return editor
