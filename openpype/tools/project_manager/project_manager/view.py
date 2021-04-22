from Qt import QtWidgets, QtCore

from .constants import (
    IDENTIFIER_ROLE,
    COLUMNS_ROLE
)
from .delegates import NumberDelegate, StringDelegate


class HierarchyView(QtWidgets.QTreeView):
    """A tree view that deselects on clicking on an empty area in the view"""
    column_delegate_defs = {
        "name": StringDelegate,
        "frameStart": NumberDelegate,
        "frameEnd": NumberDelegate,
        "fps": NumberDelegate,
        "resolutionWidth": NumberDelegate,
        "resolutionHeight": NumberDelegate
    }
    persistent_columns = [
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight"
    ]

    def __init__(self, source_model, *args, **kwargs):
        super(HierarchyView, self).__init__(*args, **kwargs)
        self._source_model = source_model

        main_delegate = QtWidgets.QStyledItemDelegate()
        self.setItemDelegate(main_delegate)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(HierarchyView.ContiguousSelection)

        column_delegates = {}
        column_key_to_index = {}
        for key, delegate_klass in self.column_delegate_defs.items():
            delegate = delegate_klass()
            column = self._source_model.columns.index(key)
            self.setItemDelegateForColumn(column, delegate)
            column_delegates[key] = delegate
            column_key_to_index[key] = column

        self._delegate = main_delegate
        self._column_delegates = column_delegates
        self._column_key_to_index = column_key_to_index

    def commitData(self, editor):
        super(HierarchyView, self).commitData(editor)
        current_index = self.currentIndex()
        column = current_index.column()
        row = current_index.row()
        skipped_index = None
        if column > 0:
            indexes = []
            for index in self.selectedIndexes():
                if index.column() == column:
                    if index.row() == row:
                        skipped_index = index
                    else:
                        indexes.append(index)

            if skipped_index is not None:
                value = current_index.data(QtCore.Qt.EditRole)
                for index in indexes:
                    index.model().setData(index, value, QtCore.Qt.EditRole)

        # Update children data
        self.updateEditorData()

    def _deselect_editor(self, editor):
        if editor:
            if isinstance(editor, QtWidgets.QSpinBox):
                line_edit = editor.findChild(QtWidgets.QLineEdit)
                line_edit.deselect()

            elif isinstance(editor, QtWidgets.QLineEdit):
                editor.deselect()

    def edit(self, index, *args, **kwargs):
        result = super(HierarchyView, self).edit(index, *args, **kwargs)
        self._deselect_editor(self.indexWidget(index))
        return result

    def openPersistentEditor(self, index):
        super(HierarchyView, self).openPersistentEditor(index)
        self._deselect_editor(self.indexWidget(index))

    def rowsInserted(self, parent_index, start, end):
        super(HierarchyView, self).rowsInserted(parent_index, start, end)

        for row in range(start, end + 1):
            index = self._source_model.index(row, 0, parent_index)
            columns = index.data(COLUMNS_ROLE) or []
            for key, column in self._column_key_to_index.items():
                if key not in self.persistent_columns:
                    continue
                col_index = self._source_model.index(row, column, parent_index)
                self.openPersistentEditor(col_index)

        # Expand parent on insert
        if not self.isExpanded(parent_index):
            self.expand(parent_index)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            # clear the selection
            self.clearSelection()
            # clear the current index
            self.setCurrentIndex(QtCore.QModelIndex())

        super(HierarchyView, self).mousePressEvent(event)

    def keyPressEvent(self, event):
        call_super = False
        if event.key() == QtCore.Qt.Key_Delete:
            self._delete_item()

        elif event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            mdfs = event.modifiers()
            if mdfs == (QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier):
                self._on_ctrl_shift_enter_pressed()
            elif mdfs == QtCore.Qt.ShiftModifier:
                self._on_shift_enter_pressed()
            else:
                if self.state() == HierarchyView.NoState:
                    self._on_enter_pressed()

        elif event.modifiers() == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_Left:
                self._on_left_ctrl_pressed()
            elif event.key() == QtCore.Qt.Key_Right:
                self._on_right_ctrl_pressed()
            elif event.key() == QtCore.Qt.Key_Up:
                self._on_up_ctrl_pressed()
            elif event.key() == QtCore.Qt.Key_Down:
                self._on_down_ctrl_pressed()
        else:
            call_super = True

        if call_super:
            super(HierarchyView, self).keyPressEvent(event)
        else:
            event.accept()

    def _delete_item(self):
        index = self.currentIndex()
        self._source_model.remove_index(index)

    def _on_ctrl_shift_enter_pressed(self):
        index = self.currentIndex()
        if not index.isValid():
            return

        new_index = self._source_model.add_new_task(index)
        if new_index is None:
            return

        # Stop editing
        self.setState(HierarchyView.NoState)
        QtWidgets.QApplication.processEvents()

        # Change current index
        self.setCurrentIndex(new_index)
        # Start editing
        self.edit(new_index)

    def _on_shift_enter_pressed(self):
        index = self.currentIndex()
        if not index.isValid():
            return

        # Stop editing
        self.setState(HierarchyView.NoState)
        QtWidgets.QApplication.processEvents()

        new_index = self._source_model.add_new_asset(index)

        # Change current index
        self.setCurrentIndex(new_index)
        # Start editing
        self.edit(new_index)

    def _on_up_ctrl_pressed(self):
        self._source_model.move_horizontal(self.currentIndex(), -1)

    def _on_down_ctrl_pressed(self):
        self._source_model.move_horizontal(self.currentIndex(), 1)

    def _on_left_ctrl_pressed(self):
        self._source_model.move_vertical(self.currentIndex(), -1)

    def _on_right_ctrl_pressed(self):
        self._source_model.move_vertical(self.currentIndex(), 1)

    def _on_enter_pressed(self):
        index = self.currentIndex()
        if (
            index.isValid()
            and index.flags() & QtCore.Qt.ItemIsEditable
        ):
            self.edit(index)
