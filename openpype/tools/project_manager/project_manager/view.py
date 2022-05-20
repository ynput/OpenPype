import collections
from queue import Queue

from Qt import QtWidgets, QtCore, QtGui

from .delegates import (
    NumberDelegate,
    NameDelegate,
    TypeDelegate,
    ToolsDelegate
)

from openpype.lib import ApplicationManager
from .constants import (
    REMOVED_ROLE,
    IDENTIFIER_ROLE,
    ITEM_TYPE_ROLE,
    HIERARCHY_CHANGE_ABLE_ROLE,
    EDITOR_OPENED_ROLE
)


class NameDef:
    pass


class NumberDef:
    def __init__(self, minimum=None, maximum=None, decimals=None):
        self.minimum = 0 if minimum is None else minimum
        self.maximum = 999999 if maximum is None else maximum
        self.decimals = 0 if decimals is None else decimals


class TypeDef:
    pass


class ToolsDef:
    pass


class ProjectDocCache:
    def __init__(self, dbcon):
        self.dbcon = dbcon
        self.project_doc = None

    def set_project(self, project_name):
        self.project_doc = None

        if not project_name:
            return

        self.project_doc = self.dbcon.database[project_name].find_one(
            {"type": "project"}
        )


class ToolsCache:
    def __init__(self):
        self.tools_data = []

    def refresh(self):
        app_manager = ApplicationManager()
        tools_data = []
        for tool_name, tool in app_manager.tools.items():
            tools_data.append(
                (tool_name, tool.label)
            )
        self.tools_data = tools_data


class HierarchyView(QtWidgets.QTreeView):
    """A tree view that deselects on clicking on an empty area in the view"""
    column_delegate_defs = {
        "name": NameDef(),
        "type": TypeDef(),
        "frameStart": NumberDef(1),
        "frameEnd": NumberDef(1),
        "fps": NumberDef(1, decimals=2),
        "resolutionWidth": NumberDef(0),
        "resolutionHeight": NumberDef(0),
        "handleStart": NumberDef(0),
        "handleEnd": NumberDef(0),
        "clipIn": NumberDef(1),
        "clipOut": NumberDef(1),
        "pixelAspect": NumberDef(0, decimals=2),
        "tools_env": ToolsDef()
    }

    columns_sizes = {
        "default": {
            "stretch": QtWidgets.QHeaderView.ResizeToContents
        },
        "name": {
            "stretch": QtWidgets.QHeaderView.Interactive,
            "width": 260
        },
        "type": {
            "stretch": QtWidgets.QHeaderView.Interactive,
            "width": 140
        },
        "tools_env": {
            "stretch": QtWidgets.QHeaderView.Interactive,
            "width": 200
        }
    }
    persistent_columns = {
        "type",
        "frameStart",
        "frameEnd",
        "fps",
        "resolutionWidth",
        "resolutionHeight",
        "handleStart",
        "handleEnd",
        "clipIn",
        "clipOut",
        "pixelAspect",
        "tools_env"
    }

    def __init__(self, dbcon, source_model, parent):
        super(HierarchyView, self).__init__(parent)

        self.setObjectName("HierarchyView")

        # Direct access to model
        self._source_model = source_model
        self._editors_mapping = {}
        self._persisten_editors = set()
        # Access to parent because of `show_message` method
        self._parent = parent

        project_doc_cache = ProjectDocCache(dbcon)
        tools_cache = ToolsCache()

        main_delegate = QtWidgets.QStyledItemDelegate()
        self.setItemDelegate(main_delegate)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(HierarchyView.ExtendedSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        column_delegates = {}
        column_key_to_index = {}
        for key, item_type in self.column_delegate_defs.items():
            if isinstance(item_type, NameDef):
                delegate = NameDelegate()

            elif isinstance(item_type, NumberDef):
                delegate = NumberDelegate(
                    item_type.minimum,
                    item_type.maximum,
                    item_type.decimals
                )

            elif isinstance(item_type, TypeDef):
                delegate = TypeDelegate(project_doc_cache)

            elif isinstance(item_type, ToolsDef):
                delegate = ToolsDelegate(tools_cache)

            column = self._source_model.columns.index(key)
            self.setItemDelegateForColumn(column, delegate)
            column_delegates[key] = delegate
            column_key_to_index[key] = column

        source_model.index_moved.connect(self._on_rows_moved)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self._source_model.project_changed.connect(self._on_project_reset)

        self._project_doc_cache = project_doc_cache
        self._tools_cache = tools_cache

        self._delegate = main_delegate
        self._column_delegates = column_delegates
        self._column_key_to_index = column_key_to_index

    def header_init(self):
        header = self.header()

        default_behavior = self.columns_sizes["default"]
        widths_by_idx = {}
        for idx in range(header.count()):
            key = self._source_model.columns[idx]
            behavior = self.columns_sizes.get(key, default_behavior)
            if behavior is None:
                continue
            logical_index = header.logicalIndex(idx)
            stretch = behavior["stretch"]
            header.setSectionResizeMode(logical_index, stretch)
            width = behavior.get("width")
            if width is not None:
                widths_by_idx[idx] = width

        for idx, width in widths_by_idx.items():
            self.setColumnWidth(idx, width)

    def set_project(self, project_name, force=False):
        # Trigger helpers first
        self._project_doc_cache.set_project(project_name)
        self._tools_cache.refresh()

        # Trigger update of model after all data for delegates are filled
        self._source_model.set_project(project_name, force)

    def _on_project_reset(self):
        self.header_init()

        self.collapseAll()

        project_item = self._source_model.project_item
        if project_item:
            index = self._source_model.index_for_item(project_item)
            self.expand(index)

    def _on_rows_moved(self, index):
        parent_index = index.parent()
        if not self.isExpanded(parent_index):
            self.expand(parent_index)

    def commitData(self, editor):
        super(HierarchyView, self).commitData(editor)
        current_index = self.currentIndex()
        column = current_index.column()
        row = current_index.row()
        skipped_index = None
        # Change column from "type" to "name"
        if column == 1:
            new_index = self._source_model.index(
                current_index.row(),
                0,
                current_index.parent()
            )
            self.setCurrentIndex(new_index)
        elif column > 0:
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
            if isinstance(
                editor, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)
            ):
                line_edit = editor.findChild(QtWidgets.QLineEdit)
                line_edit.deselect()

            elif isinstance(editor, QtWidgets.QLineEdit):
                editor.deselect()

    def edit(self, index, *args, **kwargs):
        result = super(HierarchyView, self).edit(index, *args, **kwargs)
        if result:
            # Mark index to not return text for DisplayRole
            editor = self.indexWidget(index)
            if (
                editor not in self._persisten_editors
                and editor not in self._editors_mapping
            ):
                self._editors_mapping[editor] = index
                self._source_model.setData(index, True, EDITOR_OPENED_ROLE)
            # Deselect content of editor
            # QUESTION not sure if we want do this all the time
            self._deselect_editor(editor)
        return result

    def closeEditor(self, editor, hint):
        if (
            editor not in self._persisten_editors
            and editor in self._editors_mapping
        ):
            index = self._editors_mapping.pop(editor)
            self._source_model.setData(index, False, EDITOR_OPENED_ROLE)
        super(HierarchyView, self).closeEditor(editor, hint)

    def openPersistentEditor(self, index):
        self._source_model.setData(index, True, EDITOR_OPENED_ROLE)
        super(HierarchyView, self).openPersistentEditor(index)
        editor = self.indexWidget(index)
        self._persisten_editors.add(editor)
        self._deselect_editor(editor)

    def closePersistentEditor(self, index):
        self._source_model.setData(index, False, EDITOR_OPENED_ROLE)
        editor = self.indexWidget(index)
        self._persisten_editors.remove(editor)
        super(HierarchyView, self).closePersistentEditor(index)

    def rowsInserted(self, parent_index, start, end):
        super(HierarchyView, self).rowsInserted(parent_index, start, end)

        for row in range(start, end + 1):
            for key, column in self._column_key_to_index.items():
                if key not in self.persistent_columns:
                    continue
                col_index = self._source_model.index(row, column, parent_index)
                if bool(
                    self._source_model.flags(col_index)
                    & QtCore.Qt.ItemIsEditable
                ):
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
            self._delete_items()

        elif event.matches(QtGui.QKeySequence.Copy):
            self._copy_items()

        elif event.matches(QtGui.QKeySequence.Paste):
            self._paste_items()

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

    def _copy_items(self, indexes=None):
        try:
            if indexes is None:
                indexes = self.selectedIndexes()
            mime_data = self._source_model.copy_mime_data(indexes)

            QtWidgets.QApplication.clipboard().setMimeData(mime_data)
            self._show_message("Tasks copied")
        except ValueError as exc:
            self._show_message(str(exc))

    def _paste_items(self):
        mime_data = QtWidgets.QApplication.clipboard().mimeData()
        rows = self.selectionModel().selectedRows()
        self._source_model.paste(rows, mime_data)

    def _delete_items(self, indexes=None):
        if indexes is None:
            indexes = self.selectedIndexes()
        self._source_model.delete_indexes(indexes)

    def _on_ctrl_shift_enter_pressed(self):
        self._add_task_and_edit()

    def add_asset(self, parent_index=None):
        if parent_index is None:
            parent_index = self.currentIndex()

        if not parent_index.isValid():
            return

        # Stop editing
        self.setState(HierarchyView.NoState)
        QtWidgets.QApplication.processEvents()

        return self._source_model.add_new_asset(parent_index)

    def add_task(self, parent_index=None):
        if parent_index is None:
            parent_index = self.currentIndex()

        if not parent_index.isValid():
            return

        return self._source_model.add_new_task(parent_index)

    def _add_asset_action(self):
        self._add_asset_and_edit()

    def _add_asset_and_edit(self, parent_index=None):
        new_index = self.add_asset(parent_index)
        if new_index is None:
            return

        # Change current index
        self.selectionModel().setCurrentIndex(
            new_index,
            QtCore.QItemSelectionModel.Clear
            | QtCore.QItemSelectionModel.Select
        )
        # Start editing
        self.edit(new_index)

    def _add_task_action(self):
        self._add_task_and_edit()

    def _add_task_and_edit(self):
        new_index = self.add_task()
        if new_index is None:
            return

        # Stop editing
        self.setState(HierarchyView.NoState)
        QtWidgets.QApplication.processEvents()

        # TODO change hardcoded column index to coded
        task_type_index = self._source_model.index(
            new_index.row(), 1, new_index.parent()
        )
        # Change current index
        self.selectionModel().setCurrentIndex(
            task_type_index,
            QtCore.QItemSelectionModel.Clear
            | QtCore.QItemSelectionModel.Select
        )
        # Start editing
        self.edit(task_type_index)

    def _on_shift_enter_pressed(self):
        parent_index = self.currentIndex()
        if not parent_index.isValid():
            return

        if parent_index.data(ITEM_TYPE_ROLE) == "asset":
            parent_index = parent_index.parent()
        self._add_asset_and_edit(parent_index)

    def _on_up_ctrl_pressed(self):
        indexes = self.selectedIndexes()
        self._source_model.move_vertical(indexes, -1)

    def _on_down_ctrl_pressed(self):
        indexes = self.selectedIndexes()
        self._source_model.move_vertical(indexes, 1)

    def _on_left_ctrl_pressed(self):
        indexes = self.selectedIndexes()
        self._source_model.move_horizontal(indexes, -1)

    def _on_right_ctrl_pressed(self):
        indexes = self.selectedIndexes()
        self._source_model.move_horizontal(indexes, 1)

    def _on_enter_pressed(self):
        index = self.currentIndex()
        if (
            index.isValid()
            and index.flags() & QtCore.Qt.ItemIsEditable
        ):
            self.edit(index)

    def _remove_delete_flag(self, item_ids):
        """Remove deletion flag on items marked for deletion."""
        self._source_model.remove_delete_flag(item_ids)

    def _expand_items(self, indexes):
        """Expand multiple items with all it's children.

        Args:
            indexes (list): List of QModelIndex that should be expanded.
        """
        process_queue = Queue()
        for index in indexes:
            if index.column() == 0:
                process_queue.put(index)

        item_ids = set()
        # Use deque as expanding not visible items as first is faster
        indexes_deque = collections.deque()
        while not process_queue.empty():
            index = process_queue.get()
            item_id = index.data(IDENTIFIER_ROLE)
            if item_id in item_ids:
                continue
            item_ids.add(item_id)

            indexes_deque.append(index)

            for row in range(self._source_model.rowCount(index)):
                process_queue.put(self._source_model.index(
                    row, 0, index
                ))

        while indexes_deque:
            self.expand(indexes_deque.pop())

    def _collapse_items(self, indexes):
        """Collapse multiple items with all it's children.

        Args:
            indexes (list): List of QModelIndex that should be collapsed.
        """
        item_ids = set()
        process_queue = Queue()
        for index in indexes:
            if index.column() == 0:
                process_queue.put(index)

        while not process_queue.empty():
            index = process_queue.get()
            item_id = index.data(IDENTIFIER_ROLE)
            if item_id in item_ids:
                continue
            item_ids.add(item_id)

            self.collapse(index)

            for row in range(self._source_model.rowCount(index)):
                process_queue.put(self._source_model.index(
                    row, 0, index
                ))

    def _show_message(self, message):
        """Show message to user."""
        self._parent.show_message(message)

    def _on_context_menu(self, point):
        """Context menu on right click.

        Currently is menu shown only on "name" column.
        """
        index = self.indexAt(point)
        column = index.column()
        if column != 0:
            return

        actions = []

        context_menu = QtWidgets.QMenu(self)

        indexes = self.selectedIndexes()

        items_by_id = {}
        for index in indexes:
            if index.column() != column:
                continue

            item_id = index.data(IDENTIFIER_ROLE)
            items_by_id[item_id] = self._source_model.items_by_id[item_id]

        item_ids = tuple(items_by_id.keys())
        if len(item_ids) == 1:
            item = items_by_id[item_ids[0]]
            item_type = item.data(ITEM_TYPE_ROLE)
            if item_type in ("asset", "project"):
                add_asset_action = QtWidgets.QAction("Add Asset", context_menu)
                add_asset_action.triggered.connect(
                    self._add_asset_action
                )
                actions.append(add_asset_action)

            if item_type in ("asset", "task"):
                add_task_action = QtWidgets.QAction("Add Task", context_menu)
                add_task_action.triggered.connect(
                    self._add_task_action
                )
                actions.append(add_task_action)

        # Remove delete tag on items
        removed_item_ids = []
        show_delete_items = False
        for item_id, item in items_by_id.items():
            if item.data(REMOVED_ROLE):
                removed_item_ids.append(item_id)
            elif (
                not show_delete_items
                and item.data(ITEM_TYPE_ROLE) != "project"
                and item.data(HIERARCHY_CHANGE_ABLE_ROLE)
            ):
                show_delete_items = True

        if show_delete_items:
            action = QtWidgets.QAction("Delete items", context_menu)
            action.triggered.connect(
                lambda: self._delete_items()
            )
            actions.append(action)

        if removed_item_ids:
            action = QtWidgets.QAction("Keep items", context_menu)
            action.triggered.connect(
                lambda: self._remove_delete_flag(removed_item_ids)
            )
            actions.append(action)

        # Collapse/Expand action
        show_collapse_expand_action = False
        for item_id in item_ids:
            item = items_by_id[item_id]
            item_type = item.data(ITEM_TYPE_ROLE)
            if item_type != "task":
                show_collapse_expand_action = True
                break

        if show_collapse_expand_action:
            expand_action = QtWidgets.QAction("Expand all", context_menu)
            collapse_action = QtWidgets.QAction("Collapse all", context_menu)
            expand_action.triggered.connect(
                lambda: self._expand_items(indexes)
            )
            collapse_action.triggered.connect(
                lambda: self._collapse_items(indexes)
            )
            actions.append(expand_action)
            actions.append(collapse_action)

        if not actions:
            return

        for action in actions:
            context_menu.addAction(action)

        global_point = self.viewport().mapToGlobal(point)
        context_menu.exec_(global_point)
