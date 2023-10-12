from qtpy import QtWidgets, QtGui, QtCore

from openpype.style import get_disabled_entity_icon_color
from openpype.tools.utils import DeselectableTreeView

from .utils import RefreshThread, get_qt_icon

TASKS_MODEL_SENDER_NAME = "qt_tasks_model"
ITEM_ID_ROLE = QtCore.Qt.UserRole + 1
PARENT_ID_ROLE = QtCore.Qt.UserRole + 2
ITEM_NAME_ROLE = QtCore.Qt.UserRole + 3
TASK_TYPE_ROLE = QtCore.Qt.UserRole + 4


class TasksModel(QtGui.QStandardItemModel):
    """Tasks model which cares about refresh of tasks by folder id.

    Args:
        controller (AbstractWorkfilesFrontend): The control object.
    """

    refreshed = QtCore.Signal()

    def __init__(self, controller):
        super(TasksModel, self).__init__()

        self._controller = controller

        self._items_by_name = {}
        self._has_content = False
        self._is_refreshing = False

        self._invalid_selection_item_used = False
        self._invalid_selection_item = None
        self._empty_tasks_item_used = False
        self._empty_tasks_item = None

        self._last_project_name = None
        self._last_folder_id = None

        self._refresh_threads = {}
        self._current_refresh_thread = None

        # Initial state
        self._add_invalid_selection_item()

    def _clear_items(self):
        self._items_by_name = {}
        self._has_content = False
        self._remove_invalid_items()
        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())

    def refresh(self):
        """Refresh tasks for last project and folder."""

        self._refresh(self._last_project_name, self._last_folder_id)

    def set_context(self, project_name, folder_id):
        """Set context for which should be tasks showed.

        Args:
            project_name (Union[str]): Name of project.
            folder_id (Union[str, None]): Folder id.
        """

        self._refresh(project_name, folder_id)

    def get_index_by_name(self, task_name):
        """Find item by name and return its index.

        Returns:
            QtCore.QModelIndex: Index of item. Is invalid if task is not
                found by name.
        """

        item = self._items_by_name.get(task_name)
        if item is None:
            return QtCore.QModelIndex()
        return self.indexFromItem(item)

    def get_last_project_name(self):
        """Get last refreshed project name.

        Returns:
            Union[str, None]: Project name.
        """

        return self._last_project_name

    def get_last_folder_id(self):
        """Get last refreshed folder id.

        Returns:
            Union[str, None]: Folder id.
        """

        return self._last_folder_id

    def set_selected_project(self, project_name):
        self._selected_project_name = project_name

    def _get_invalid_selection_item(self):
        if self._invalid_selection_item is None:
            item = QtGui.QStandardItem("Select a folder")
            item.setFlags(QtCore.Qt.NoItemFlags)
            icon = get_qt_icon({
                "type": "awesome-font",
                "name": "fa.times",
                "color": get_disabled_entity_icon_color(),
            })
            item.setData(icon, QtCore.Qt.DecorationRole)
            self._invalid_selection_item = item
        return self._invalid_selection_item

    def _get_empty_task_item(self):
        if self._empty_tasks_item is None:
            item = QtGui.QStandardItem("No task")
            icon = get_qt_icon({
                "type": "awesome-font",
                "name": "fa.exclamation-circle",
                "color": get_disabled_entity_icon_color(),
            })
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self._empty_tasks_item = item
        return self._empty_tasks_item

    def _add_invalid_item(self, item):
        self._clear_items()
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

    def _refresh(self, project_name, folder_id):
        self._is_refreshing = True
        self._last_project_name = project_name
        self._last_folder_id = folder_id
        if not folder_id:
            self._add_invalid_selection_item()
            self._current_refresh_thread = None
            self._is_refreshing = False
            self.refreshed.emit()
            return

        thread = self._refresh_threads.get(folder_id)
        if thread is not None:
            self._current_refresh_thread = thread
            return
        thread = RefreshThread(
            folder_id,
            self._controller.get_task_items,
            project_name,
            folder_id
        )
        self._current_refresh_thread = thread
        self._refresh_threads[thread.id] = thread
        thread.refresh_finished.connect(self._on_refresh_thread)
        thread.start()

    def _on_refresh_thread(self, thread_id):
        """Callback when refresh thread is finished.

        Technically can be running multiple refresh threads at the same time,
        to avoid using values from wrong thread, we check if thread id is
        current refresh thread id.

        Tasks are stored by name, so if a folder has same task name as
        previously selected folder it keeps the selection.

        Args:
            thread_id (str): Thread id.
        """

        # Make sure to remove thread from '_refresh_threads' dict
        thread = self._refresh_threads.pop(thread_id)
        if (
            self._current_refresh_thread is None
            or thread_id != self._current_refresh_thread.id
        ):
            return

        task_items = thread.get_result()
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
            icon = get_qt_icon(task_item.icon)
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
        self._is_refreshing = False
        self.refreshed.emit()

    @property
    def is_refreshing(self):
        """Model is refreshing.

        Returns:
            bool: Model is refreshing
        """

        return self._is_refreshing

    @property
    def has_content(self):
        """Model has content.

        Returns:
            bools: Have at least one task.
        """

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
    """Tasks widget.

    Widget that handles tasks view, model and selection.

    Args:
        controller (AbstractWorkfilesFrontend): Workfiles controller.
        parent (QtWidgets.QWidget): Parent widget.
        handle_expected_selection (Optional[bool]): Handle expected selection.
    """

    def __init__(self, controller, parent, handle_expected_selection=False):
        super(TasksWidget, self).__init__(parent)

        tasks_view = DeselectableTreeView(self)
        tasks_view.setIndentation(0)

        tasks_model = TasksModel(controller)
        tasks_proxy_model = QtCore.QSortFilterProxyModel()
        tasks_proxy_model.setSourceModel(tasks_model)
        tasks_proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        tasks_view.setModel(tasks_proxy_model)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(tasks_view, 1)

        controller.register_event_callback(
            "tasks.refresh.finished",
            self._on_tasks_refresh_finished
        )
        controller.register_event_callback(
            "selection.folder.changed",
            self._folder_selection_changed
        )
        controller.register_event_callback(
            "expected_selection_changed",
            self._on_expected_selection_change
        )

        selection_model = tasks_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)

        tasks_model.refreshed.connect(self._on_tasks_model_refresh)

        self._controller = controller
        self._tasks_view = tasks_view
        self._tasks_model = tasks_model
        self._tasks_proxy_model = tasks_proxy_model

        self._selected_folder_id = None

        self._handle_expected_selection = handle_expected_selection
        self._expected_selection_data = None

    def refresh(self):
        """Refresh folders for last selected project.

        Force to update folders model from controller. This may or may not
        trigger query from server, that's based on controller's cache.
        """

        self._tasks_model.refresh()

    def _on_tasks_refresh_finished(self, event):
        """Tasks were refreshed in controller.

        Ignore if refresh was triggered by tasks model, or refreshed folder is
        not the same as currently selected folder.

        Args:
            event (Event): Event object.
        """

        # Refresh only if current folder id is the same
        if (
            event["sender"] == TASKS_MODEL_SENDER_NAME
            or event["folder_id"] != self._selected_folder_id
        ):
            return
        self._tasks_model.set_context(
            event["project_name"], self._selected_folder_id
        )

    def _folder_selection_changed(self, event):
        self._selected_folder_id = event["folder_id"]
        self._tasks_model.set_context(
            event["project_name"], self._selected_folder_id
        )

    def _on_tasks_model_refresh(self):
        if not self._set_expected_selection():
            self._on_selection_change()
        self._tasks_proxy_model.sort(0)

    def _get_selected_item_ids(self):
        selection_model = self._tasks_view.selectionModel()
        for index in selection_model.selectedIndexes():
            task_id = index.data(ITEM_ID_ROLE)
            task_name = index.data(ITEM_NAME_ROLE)
            parent_id = index.data(PARENT_ID_ROLE)
            if task_name is not None:
                return parent_id, task_id, task_name
        return self._selected_folder_id, None, None

    def _on_selection_change(self):
        # Don't trigger task change during refresh
        #   - a task was deselected if that happens
        #   - can cause crash triggered during tasks refreshing
        if self._tasks_model.is_refreshing:
            return

        parent_id, task_id, task_name = self._get_selected_item_ids()
        self._controller.set_selected_task(task_id, task_name)

    # Expected selection handling
    def _on_expected_selection_change(self, event):
        self._update_expected_selection(event.data)

    def _set_expected_selection(self):
        if not self._handle_expected_selection:
            return False

        if self._expected_selection_data is None:
            return False
        folder_id = self._expected_selection_data["folder_id"]
        task_name = self._expected_selection_data["task_name"]
        self._expected_selection_data = None
        model_folder_id = self._tasks_model.get_last_folder_id()
        if folder_id != model_folder_id:
            return False
        if task_name is not None:
            index = self._tasks_model.get_index_by_name(task_name)
            if index.isValid():
                proxy_index = self._tasks_proxy_model.mapFromSource(index)
                self._tasks_view.setCurrentIndex(proxy_index)
        self._controller.expected_task_selected(folder_id, task_name)
        return True

    def _update_expected_selection(self, expected_data=None):
        if not self._handle_expected_selection:
            return
        if expected_data is None:
            expected_data = self._controller.get_expected_selection_data()
        folder_data = expected_data.get("folder")
        task_data = expected_data.get("task")
        if (
            not folder_data
            or not task_data
            or not task_data["current"]
        ):
            return
        folder_id = folder_data["id"]
        self._expected_selection_data = {
            "task_name": task_data["name"],
            "folder_id": folder_id,
        }
        model_folder_id = self._tasks_model.get_last_folder_id()
        if folder_id != model_folder_id or self._tasks_model.is_refreshing:
            return
        self._set_expected_selection()
