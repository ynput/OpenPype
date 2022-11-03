from Qt import QtWidgets, QtCore, QtGui

import qtawesome
import typing

from openpype.client import (
    get_project,
    get_asset_by_id,
)

from . import widgets
from .views import DeselectableTreeView

from openpype.style import get_disabled_entity_icon_color
from openpype.tools.utils.lib import get_task_icon

_typing = False
if _typing:
    from typing import Any
del _typing


TASK_NAME_ROLE = QtCore.Qt.UserRole + 1
TASK_TYPE_ROLE = QtCore.Qt.UserRole + 2
TASK_ORDER_ROLE = QtCore.Qt.UserRole + 3
TASK_ASSIGNEE_ROLE = QtCore.Qt.UserRole + 4


class TaskViewItem(QtGui.QStandardItem):

    def __init__(self, task_name, task_info, asset_doc, project_doc, task_type_in_label=True):
        # type: (str, dict[str, Any], dict[str, Any], dict[str, Any] | None, bool) -> None
        task_type = task_info.get("type")  # type: str | None
        label = "{} ({})".format(task_name, task_type or "type N/A") if task_type_in_label else task_name
        super(TaskViewItem, self).__init__(label)

        task_assignees = set()                              # type: set[str]
        assignees_data = task_info.get("assignees") or []   # list[dict[str, str]]
        for assignee in assignees_data:
            username = assignee.get("username")  # type: str
            if username:
                task_assignees.add(username)

        icon = get_task_icon(project_doc, asset_doc, task_name)
        task_order = task_info.get("order") # type: int | None

        self.setData(task_name, TASK_NAME_ROLE)
        self.setData(task_type, TASK_TYPE_ROLE)
        self.setData(task_order, TASK_ORDER_ROLE)
        self.setData(task_assignees, TASK_ASSIGNEE_ROLE)
        self.setData(icon, QtCore.Qt.DecorationRole)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)


class TasksModel(QtGui.QStandardItemModel):
    """A model listing the tasks combined for a list of assets"""

    def __init__(self, dbcon, parent=None):
        super(TasksModel, self).__init__(parent=parent)
        self.dbcon = dbcon

        self._no_tasks_icon = qtawesome.icon(
            "fa.exclamation-circle",
            color=get_disabled_entity_icon_color()
        )
        self._cached_icons = {}
        self._project_doc = {}

        self._empty_tasks_item = None
        self._last_asset_id = None
        self._loaded_project_name = None

    def _context_is_valid(self):
        if self._get_current_project():
            return True
        return False

    def refresh(self):
        self._refresh_project_doc()
        self.set_asset_id(self._last_asset_id)

    def _refresh_project_doc(self):
        # Get the project configured icons from database
        project_doc = {}
        if self._context_is_valid():
            project_name = self.dbcon.active_project()
            project_doc = get_project(project_name)

        self._loaded_project_name = self._get_current_project()
        self._project_doc = project_doc

    def headerData(self, section, orientation, role=None):
        if role is None:
            role = QtCore.Qt.EditRole
        # Show nice labels in the header
        if section == 0:
            if (
                role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole)
                and orientation == QtCore.Qt.Horizontal
            ):
                return "Tasks"

        return super(TasksModel, self).headerData(section, orientation, role)

    def _get_current_project(self):
        return self.dbcon.Session.get("AVALON_PROJECT")

    def set_asset_id(self, asset_id):
        asset_doc = None
        if self._context_is_valid():
            project_name = self._get_current_project()
            asset_doc = get_asset_by_id(
                project_name, asset_id, fields=["data.tasks"]
            )
        self._set_asset(asset_doc)

    def _get_empty_task_item(self):
        if self._empty_tasks_item is None:
            item = QtGui.QStandardItem("No task")
            item.setData(self._no_tasks_icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self._empty_tasks_item = item
        return self._empty_tasks_item

    def _get_view_item(self, task_name, task_info, asset_doc):
        # type: (str, dict[str, Any], dict[str, Any]) -> TaskViewItem
        """
        Dependency injection to allow the task view item class to be
        overriden in child classes.
        """
        return TaskViewItem(task_name, task_info, asset_doc, self._project_doc)

    def _create_task_items(self, asset_doc, asset_tasks):
        # type: (dict[str, Any], dict[str, Any]) -> list[TaskViewItem | QtGui.QStandardItem]
        items = []  # type: list[TaskViewItem | QtGui.QStandardItem]
        for task_name, task_info in asset_tasks.items():
            item = self._get_view_item(task_name, task_info, asset_doc)
            items.append(item)

        if not items:
            item = QtGui.QStandardItem("No tasks!")
            item.setData(self._no_tasks_icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            items.append(item)
        return items

    def _set_asset(self, asset_doc):
        # type: (dict[str, Any]) -> None
        """Set assets to track by their database id

        Arguments:
            asset_doc (dict): Asset document from MongoDB.
        """
        if self._loaded_project_name != self._get_current_project():
            self._refresh_project_doc()

        asset_tasks = {}
        self._last_asset_id = None
        if asset_doc:
            asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
            self._last_asset_id = asset_doc["_id"]

        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())
        items = self._create_task_items(asset_doc, asset_tasks)
        root_item.appendRows(items)


class TasksProxyModel(QtCore.QSortFilterProxyModel):
    def lessThan(self, x_index, y_index):
        x_order = x_index.data(TASK_ORDER_ROLE)
        y_order = y_index.data(TASK_ORDER_ROLE)
        if x_order is not None and y_order is not None:
            if x_order < y_order:
                return True
            if x_order > y_order:
                return False

        elif x_order is None and y_order is not None:
            return True

        elif y_order is None and x_order is not None:
            return False

        x_name = x_index.data(QtCore.Qt.DisplayRole)
        y_name = y_index.data(QtCore.Qt.DisplayRole)
        if x_name == y_name:
            return True

        if x_name == tuple(sorted((x_name, y_name)))[0]:
            return True
        return False


class TaskTreeView(DeselectableTreeView):
    def __init__(self, *args, **kwargs):
        super(TaskTreeView, self).__init__(*args, **kwargs)
        self.setHeaderHidden(True)


class TasksWidget(widgets.ItemViewWidget):
    """Widget showing active Tasks"""

    task_changed = QtCore.Signal()

    if typing.TYPE_CHECKING:
        _model = None   # type: TasksModel
        _proxy = None   # type: TasksProxyModel
        _view = None    # type: TaskTreeView

    def __init__(self, dbcon, parent=None, show_search_bar=False):
        self._dbcon = dbcon

        super(TasksWidget, self).__init__(dbcon, TaskTreeView, "Tasks", parent=parent, show_search_bar=show_search_bar)

        self._view.setIndentation(0)
        self._view.setSortingEnabled(True)
        self._view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)

        header_view = self._view.header()
        header_view.setSortIndicator(0, QtCore.Qt.AscendingOrder)

        self._tasks_model = self._model
        self._tasks_proxy = self._proxy
        self._tasks_view = self._view

        self._last_selected_task_name = None

    def _create_source_model(self):
        """Create source model of tasks widget.

        Model must have available 'refresh' method and 'set_asset_id' to change
        context of asset.
        """
        return TasksModel(self._dbcon)

    def _create_proxy_model(self, source_model):
        proxy = TasksProxyModel()
        proxy.setSourceModel(source_model)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        return proxy

    def refresh(self):
        self._tasks_model.refresh()

    def set_asset_id(self, asset_id):
        # Try and preserve the last selected task and reselect it
        # after switching assets. If there's no currently selected
        # asset keep whatever the "last selected" was prior to it.
        current = self.get_selected_task_name()

        self._tasks_model.set_asset_id(asset_id)

        if self._last_selected_task_name:
            self.select_task_name(self._last_selected_task_name)

        if current:
            self._last_selected_task_name = current

    def _clear_selection(self):
        selection_model = self._tasks_view.selectionModel()
        selection_model.clearSelection()

    def select_task_name(self, task_name):
        # type: (str) -> None
        """Select a task by name.

        If the task does not exist in the current model then selection is only
        cleared.

        Args:
            task (str): Name of the task to select.

        """
        task_view_model = self._tasks_view.model()
        if not task_view_model:
            return

        # Clear selection
        selection_model = self._tasks_view.selectionModel()
        # @sharkmob-shea.richardson:
        # We block signals from being emitted whilst updating
        # the selection is cleared.
        # This removes redundant signals being sent:
        selection_model.blockSignals(True)
        selection_model.clearSelection()
        selection_model.blockSignals(False)

        # Select the task
        mode = selection_model.Select | selection_model.Rows
        for row in range(task_view_model.rowCount()):
            index = task_view_model.index(row, 0)
            name = index.data(TASK_NAME_ROLE)  # type: str
            if name != task_name:
                continue

            selection_model.select(index, mode)

            # Set the currently active index
            self._tasks_view.setCurrentIndex(index)
            break

        selected_task_name = self.get_selected_task_name()
        if selected_task_name:
            self._last_selected_task_name = selected_task_name
            self.task_changed.emit()

    def get_selected_task_name(self):
        """Return name of task at current index (selected)

        Returns:
            str: Name of the current task.

        """
        index = self._tasks_view.currentIndex()
        selection_model = self._tasks_view.selectionModel()
        if index.isValid() and selection_model.isSelected(index):
            return index.data(TASK_NAME_ROLE)
        return None

    def get_selected_task_type(self):
        index = self._tasks_view.currentIndex()
        selection_model = self._tasks_view.selectionModel()
        if index.isValid() and selection_model.isSelected(index):
            return index.data(TASK_TYPE_ROLE)
        return None

    def _on_selection_change(self):
        self.task_changed.emit()