from Qt import QtWidgets, QtCore, QtGui
import qtawesome

from openpype.style import (
    get_default_entity_icon_color,
    get_disabled_entity_icon_color,
)

from .views import DeselectableTreeView


TASK_NAME_ROLE = QtCore.Qt.UserRole + 1
TASK_TYPE_ROLE = QtCore.Qt.UserRole + 2
TASK_ORDER_ROLE = QtCore.Qt.UserRole + 3
TASK_ASSIGNEE_ROLE = QtCore.Qt.UserRole + 4


class TasksModel(QtGui.QStandardItemModel):
    """A model listing the tasks combined for a list of assets"""

    def __init__(self, dbcon, parent=None):
        super(TasksModel, self).__init__(parent=parent)
        self.dbcon = dbcon
        self.setHeaderData(
            0, QtCore.Qt.Horizontal, "Tasks", QtCore.Qt.DisplayRole
        )
        default_color = get_default_entity_icon_color()
        self._default_color = default_color
        self._default_icon = qtawesome.icon(
            "fa.male", color=default_color
        )
        self._no_tasks_icon = qtawesome.icon(
            "fa.exclamation-circle",
            color=get_disabled_entity_icon_color()
        )
        self._cached_icons = {}
        self._project_task_types = {}

        self._empty_tasks_item = None
        self._last_asset_id = None
        self._loaded_project_name = None

    def _context_is_valid(self):
        if self.dbcon.Session.get("AVALON_PROJECT"):
            return True
        return False

    def refresh(self):
        self._refresh_task_types()
        self.set_asset_id(self._last_asset_id)

    def _refresh_task_types(self):
        # Get the project configured icons from database
        task_types = {}
        if self._context_is_valid():
            project = self.dbcon.find_one(
                {"type": "project"},
                {"config.tasks"}
            )
            task_types = project["config"].get("tasks") or task_types
        self._project_task_types = task_types

    def _try_get_awesome_icon(self, icon_name):
        icon = None
        if icon_name:
            try:
                icon = qtawesome.icon(
                    "fa.{}".format(icon_name),
                    color=self._default_color
                )

            except Exception:
                pass
        return icon

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

    def _get_icon(self, task_icon, task_type_icon):
        if task_icon in self._cached_icons:
            return self._cached_icons[task_icon]

        icon = self._try_get_awesome_icon(task_icon)
        if icon is not None:
            self._cached_icons[task_icon] = icon
            return icon

        if task_type_icon in self._cached_icons:
            icon = self._cached_icons[task_type_icon]
            self._cached_icons[task_icon] = icon
            return icon

        icon = self._try_get_awesome_icon(task_type_icon)
        if icon is None:
            icon = self._default_icon

        self._cached_icons[task_icon] = icon
        self._cached_icons[task_type_icon] = icon

        return icon

    def set_asset_id(self, asset_id):
        asset_doc = None
        if self._context_is_valid():
            asset_doc = self.dbcon.find_one(
                {"_id": asset_id},
                {"data.tasks": True}
            )
        self._set_asset(asset_doc)

    def _get_empty_task_item(self):
        if self._empty_tasks_item is None:
            item = QtGui.QStandardItem("No task")
            item.setData(self._no_tasks_icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self._empty_tasks_item = item
        return self._empty_tasks_item

    def _set_asset(self, asset_doc):
        """Set assets to track by their database id

        Arguments:
            asset_doc (dict): Asset document from MongoDB.
        """
        asset_tasks = {}
        self._last_asset_id = None
        if asset_doc:
            asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
            self._last_asset_id = asset_doc["_id"]

        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())

        items = []
        for task_name, task_info in asset_tasks.items():
            task_icon = task_info.get("icon")
            task_type = task_info.get("type")
            task_order = task_info.get("order")
            task_type_info = self._project_task_types.get(task_type) or {}
            task_type_icon = task_type_info.get("icon")
            icon = self._get_icon(task_icon, task_type_icon)

            task_assignees = set()
            assignees_data = task_info.get("assignees") or []
            for assignee in assignees_data:
                username = assignee.get("username")
                if username:
                    task_assignees.add(username)

            label = "{} ({})".format(task_name, task_type or "type N/A")
            item = QtGui.QStandardItem(label)
            item.setData(task_name, TASK_NAME_ROLE)
            item.setData(task_type, TASK_TYPE_ROLE)
            item.setData(task_order, TASK_ORDER_ROLE)
            item.setData(task_assignees, TASK_ASSIGNEE_ROLE)
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            items.append(item)

        if not items:
            item = QtGui.QStandardItem("No task")
            item.setData(self._no_tasks_icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            items.append(item)

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


class TasksWidget(QtWidgets.QWidget):
    """Widget showing active Tasks"""

    task_changed = QtCore.Signal()

    def __init__(self, dbcon, parent=None):
        self._dbcon = dbcon

        super(TasksWidget, self).__init__(parent)

        tasks_view = DeselectableTreeView(self)
        tasks_view.setIndentation(0)
        tasks_view.setSortingEnabled(True)
        tasks_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)

        header_view = tasks_view.header()
        header_view.setSortIndicator(0, QtCore.Qt.AscendingOrder)

        tasks_model = self._create_source_model()
        tasks_proxy = self._create_proxy_model(tasks_model)
        tasks_view.setModel(tasks_proxy)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tasks_view)

        selection_model = tasks_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_task_change)

        self._tasks_model = tasks_model
        self._tasks_proxy = tasks_proxy
        self._tasks_view = tasks_view

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
        return proxy

    def refresh(self):
        self._tasks_model.refresh()

    def set_asset_id(self, asset_id):
        # Try and preserve the last selected task and reselect it
        # after switching assets. If there's no currently selected
        # asset keep whatever the "last selected" was prior to it.
        current = self.get_selected_task_name()
        if current:
            self._last_selected_task_name = current

        self._tasks_model.set_asset_id(asset_id)

        if self._last_selected_task_name:
            self.select_task_name(self._last_selected_task_name)

        # Force a task changed emit.
        self.task_changed.emit()

    def _clear_selection(self):
        selection_model = self._tasks_view.selectionModel()
        selection_model.clearSelection()

    def select_task_name(self, task_name):
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
        selection_model.clearSelection()

        # Select the task
        mode = selection_model.Select | selection_model.Rows
        for row in range(task_view_model.rowCount()):
            index = task_view_model.index(row, 0)
            name = index.data(TASK_NAME_ROLE)
            if name == task_name:
                selection_model.select(index, mode)

                # Set the currently active index
                self._tasks_view.setCurrentIndex(index)
                break

        last_selected_task_name = self.get_selected_task_name()
        if last_selected_task_name:
            self._last_selected_task_name = last_selected_task_name

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

    def _on_task_change(self):
        self.task_changed.emit()
