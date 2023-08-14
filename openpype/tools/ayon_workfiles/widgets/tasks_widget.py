import qtawesome
from qtpy import QtWidgets, QtGui, QtCore

from openpype.style import get_disabled_entity_icon_color
from openpype.tools.utils import DeselectableTreeView

from .constants import (
    ITEM_NAME_ROLE,
    ITEM_ID_ROLE,
    PARENT_ID_ROLE,
)


class TasksModel(QtGui.QStandardItemModel):
    def __init__(self, control):
        super(TasksModel, self).__init__()

        self._control = control

        self._items_by_name = {}
        self._has_content = False
        self._is_refreshing = False

        self._invalid_selection_item_used = False
        self._invalid_selection_item = None
        self._empty_tasks_item_used = False
        self._empty_tasks_item = None

        # Initial state
        self._add_invalid_selection_item()

    def clear(self):
        self._items_by_name = {}
        self._has_content = False
        self._remove_invalid_items()
        super(TasksModel, self).clear()

    def refresh(self):
        self._is_refreshing = True
        try:
            self._refresh()
        finally:
            self._is_refreshing = False

    def get_index_by_name(self, task_name):
        item = self._items_by_name.get(task_name)
        if item is None:
            return QtCore.QModelIndex()
        return self.indexFromItem(item)

    def _get_invalid_selection_item(self):
        if self._invalid_selection_item is None:
            item = QtGui.QStandardItem("Select a folder")
            item.setFlags(QtCore.Qt.NoItemFlags)
            icon = qtawesome.icon(
                "fa.times",
                color=get_disabled_entity_icon_color()
            )
            item.setData(icon, QtCore.Qt.DecorationRole)
            self._invalid_selection_item = item
        return self._invalid_selection_item

    def _get_empty_task_item(self):
        if self._empty_tasks_item is None:
            item = QtGui.QStandardItem("No task")
            icon = qtawesome.icon(
                "fa.exclamation-circle",
                color=get_disabled_entity_icon_color()
            )
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self._empty_tasks_item = item
        return self._empty_tasks_item

    def _add_invalid_item(self, item):
        self.clear()
        root_item = self.invisibleRootItem()
        root_item.appendRow(item)

    def _remove_invalid_item(self, item):
        root_item = self.invisibleRootItem()
        root_item.takeRow(item.row())

    def _remove_invalid_items(self):
        self._remove_invalid_selection_item()
        self._remove_empty_task_item()

    def _add_invalid_selection_item(self):
        if not self._invalid_selection_item_used:
            self._add_invalid_item(self._get_invalid_selection_item())
            self._invalid_selection_item_used = True

    def _remove_invalid_selection_item(self):
        if self._invalid_selection_item:
            self._remove_invalid_item(self._get_invalid_selection_item())
            self._invalid_selection_item_used = False

    def _add_empty_task_item(self):
        if not self._empty_tasks_item_used:
            self._add_invalid_item(self._get_empty_task_item())
            self._empty_tasks_item_used = True

    def _remove_empty_task_item(self):
        if self._empty_tasks_item_used:
            self._remove_invalid_item(self._get_empty_task_item())
            self._empty_tasks_item_used = False

    def _refresh(self):
        folder_id = self._control.get_selected_folder_id()
        if not folder_id:
            self._add_invalid_selection_item()
            return

        task_items = self._control.get_task_items(folder_id)
        # Task items are refreshed
        if task_items is None:
            return

        # No tasks are available on folder
        if not task_items:
            self._add_empty_task_item()
            return
        self._remove_invalid_items()

        new_items = []
        new_names = set()
        for task_item in task_items:
            name = task_item.name
            new_names.add(name)
            item = self._items_by_name.get(name)
            if item is None:
                item = QtGui.QStandardItem()
                item.setEditable(False)
                new_items.append(item)
                self._items_by_name[name] = item

            # TODO cache locally
            icon = qtawesome.icon(
                task_item.icon_name,
                color=task_item.icon_color,
            )
            item.setData(task_item.label, QtCore.Qt.DisplayRole)
            item.setData(name, ITEM_NAME_ROLE)
            item.setData(task_item.id, ITEM_ID_ROLE)
            item.setData(task_item.parent_id, PARENT_ID_ROLE)
            item.setData(icon, QtCore.Qt.DecorationRole)

        root_item = self.invisibleRootItem()

        for name in set(self._items_by_name) - new_names:
            item = self._items_by_name.pop(name)
            root_item.removeRow(item.row())

        if new_items:
            root_item.appendRows(new_items)

        self._has_content = root_item.rowCount() > 0

    @property
    def is_refreshing(self):
        return self._is_refreshing

    @property
    def has_content(self):
        return self._has_content

    def headerData(self, section, orientation, role):
        # Show nice labels in the header
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
        ):
            if section == 0:
                return "Tasks"

        return super(TasksModel, self).headerData(
            section, orientation, role
        )


class TasksWidget(QtWidgets.QWidget):
    def __init__(self, control, parent):
        super(TasksWidget, self).__init__(parent)

        tasks_view = DeselectableTreeView(self)
        tasks_view.setIndentation(0)

        tasks_model = TasksModel(control)
        tasks_proxy_model = QtCore.QSortFilterProxyModel()
        tasks_proxy_model.setSourceModel(tasks_model)

        tasks_view.setModel(tasks_proxy_model)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(tasks_view, 1)

        control.register_event_callback(
            "tasks.refresh.started",
            self._on_tasks_refresh_started
        )
        control.register_event_callback(
            "tasks.refresh.finished",
            self._on_tasks_refresh_finished
        )
        control.register_event_callback(
            "selection.folder.changed",
            self._folder_selection_changed
        )
        control.register_event_callback(
            "controller.expected_selection_changed",
            self._on_expected_selection_change
        )

        selection_model = tasks_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)

        self._control = control
        self._tasks_view = tasks_view
        self._tasks_model = tasks_model
        self._tasks_proxy_model = tasks_proxy_model

        self._last_project = None
        self._last_folder_id = None

    def _clear(self):
        self._tasks_model.clear()

    def _on_tasks_refresh_started(self, event):
        if self._last_project == event["project_name"]:
            return

        if self._last_project is not None:
            self._clear()
        self._last_project = event["project_name"]

    def _on_tasks_refresh_finished(self, event):
        # Refresh only if current folder id is the same
        if (
            event["project_name"] != self._last_project
            or event["folder_id"] != self._last_folder_id
        ):
            return
        self._tasks_model.refresh()
        self._tasks_proxy_model.sort(0)

    def _folder_selection_changed(self, event):
        self._last_folder_id = event["folder_id"]
        self._tasks_model.refresh()
        # Fake trigger of selection change to update selected task
        self._on_selection_change()

    def _on_expected_selection_change(self, event):
        if event["folder_id"] != self._last_folder_id:
            return
        self._set_expected_selection(
            task_name=event["task_name"],
            folder_id=event["folder_id"],
        )

    def _set_expected_selection(self, **kwargs):
        if "task_name" in kwargs:
            task_name = kwargs["task_name"]
        else:
            task_name = self._control.get_expected_task_name()
        if task_name is None:
            return False

        self._control.set_expected_task_name(None)

        index = self._tasks_model.get_index_by_name(task_name)
        if index.isValid():
            proxy_index = self._tasks_proxy_model.mapFromSource(index)
            self._tasks_view.setCurrentIndex(proxy_index)
            return True
        return False

    def _get_selected_item_ids(self):
        selection_model = self._tasks_view.selectionModel()
        for index in selection_model.selectedIndexes():
            task_id = index.data(ITEM_ID_ROLE)
            task_name = index.data(ITEM_NAME_ROLE)
            parent_id = index.data(PARENT_ID_ROLE)
            if task_name is not None:
                return parent_id, task_id, task_name
        return self._last_folder_id, None, None

    def _on_selection_change(self):
        # Don't trigger task change during refresh
        #   - a task was deselected if that happens
        #   - can cause crash triggered during tasks refreshing
        if self._tasks_model.is_refreshing:
            return
        parent_id, task_id, task_name = self._get_selected_item_ids()
        expected_name = self._control.get_expected_task_name()
        if (
            expected_name is not None
            and task_name != expected_name
            and self._set_expected_selection(task_name=expected_name)
        ):
            return
        self._control.set_selected_task(parent_id, task_id, task_name)
