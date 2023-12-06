import collections

from qtpy import QtWidgets, QtGui, QtCore

from openpype.tools.utils import (
    RecursiveSortFilterProxyModel,
    TreeView,
)

from .utils import RefreshThread, get_qt_icon

FOLDERS_MODEL_SENDER_NAME = "qt_folders_model"
FOLDER_ID_ROLE = QtCore.Qt.UserRole + 1
FOLDER_NAME_ROLE = QtCore.Qt.UserRole + 2
FOLDER_PATH_ROLE = QtCore.Qt.UserRole + 3
FOLDER_TYPE_ROLE = QtCore.Qt.UserRole + 4


class FoldersQtModel(QtGui.QStandardItemModel):
    """Folders model which cares about refresh of folders.

    Args:
        controller (AbstractWorkfilesFrontend): The control object.
    """

    refreshed = QtCore.Signal()

    def __init__(self, controller):
        super(FoldersQtModel, self).__init__()

        self._controller = controller
        self._items_by_id = {}
        self._parent_id_by_id = {}

        self._refresh_threads = {}
        self._current_refresh_thread = None
        self._last_project_name = None

        self._has_content = False
        self._is_refreshing = False

    @property
    def is_refreshing(self):
        """Model is refreshing.

        Returns:
            bool: True if model is refreshing.
        """
        return self._is_refreshing

    @property
    def has_content(self):
        """Has at least one folder.

        Returns:
            bool: True if model has at least one folder.
        """

        return self._has_content

    def refresh(self):
        """Refresh folders for last selected project.

        Force to update folders model from controller. This may or may not
        trigger query from server, that's based on controller's cache.
        """

        self.set_project_name(self._last_project_name)

    def _clear_items(self):
        self._items_by_id = {}
        self._parent_id_by_id = {}
        self._has_content = False
        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())

    def get_index_by_id(self, item_id):
        """Get index by folder id.

        Returns:
            QtCore.QModelIndex: Index of the folder. Can be invalid if folder
                is not available.
        """
        item = self._items_by_id.get(item_id)
        if item is None:
            return QtCore.QModelIndex()
        return self.indexFromItem(item)

    def get_project_name(self):
        """Project name which model currently use.

        Returns:
            Union[str, None]: Currently used project name.
        """

        return self._last_project_name

    def set_project_name(self, project_name):
        """Refresh folders items.

        Refresh start thread because it can cause that controller can
        start query from database if folders are not cached.
        """

        if not project_name:
            self._last_project_name = project_name
            self._fill_items({})
            self._current_refresh_thread = None
            return

        self._is_refreshing = True

        if self._last_project_name != project_name:
            self._clear_items()
        self._last_project_name = project_name

        thread = self._refresh_threads.get(project_name)
        if thread is not None:
            self._current_refresh_thread = thread
            return

        thread = RefreshThread(
            project_name,
            self._controller.get_folder_items,
            project_name,
            FOLDERS_MODEL_SENDER_NAME
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

        Folders are stored by id.

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

        self._fill_items(thread.get_result())
        self._current_refresh_thread = None

    def _fill_item_data(self, item, folder_item):
        """

        Args:
            item (QtGui.QStandardItem): Item to fill data.
            folder_item (FolderItem): Folder item.
        """

        icon = get_qt_icon(folder_item.icon)
        item.setData(folder_item.entity_id, FOLDER_ID_ROLE)
        item.setData(folder_item.name, FOLDER_NAME_ROLE)
        item.setData(folder_item.path, FOLDER_PATH_ROLE)
        item.setData(folder_item.folder_type, FOLDER_TYPE_ROLE)
        item.setData(folder_item.label, QtCore.Qt.DisplayRole)
        item.setData(icon, QtCore.Qt.DecorationRole)

    def _fill_items(self, folder_items_by_id):
        if not folder_items_by_id:
            if folder_items_by_id is not None:
                self._clear_items()
            self._is_refreshing = False
            self.refreshed.emit()
            return

        self._has_content = True

        folder_ids = set(folder_items_by_id)
        ids_to_remove = set(self._items_by_id) - folder_ids

        folder_items_by_parent = collections.defaultdict(dict)
        for folder_item in folder_items_by_id.values():
            (
                folder_items_by_parent
                [folder_item.parent_id]
                [folder_item.entity_id]
            ) = folder_item

        hierarchy_queue = collections.deque()
        hierarchy_queue.append((self.invisibleRootItem(), None))

        # Keep pointers to removed items until the refresh finishes
        #   - some children of the items could be moved and reused elsewhere
        removed_items = []
        while hierarchy_queue:
            item = hierarchy_queue.popleft()
            parent_item, parent_id = item
            folder_items = folder_items_by_parent[parent_id]

            items_by_id = {}
            folder_ids_to_add = set(folder_items)
            for row_idx in reversed(range(parent_item.rowCount())):
                child_item = parent_item.child(row_idx)
                child_id = child_item.data(FOLDER_ID_ROLE)
                if child_id in ids_to_remove:
                    removed_items.append(parent_item.takeRow(row_idx))
                else:
                    items_by_id[child_id] = child_item

            new_items = []
            for item_id in folder_ids_to_add:
                folder_item = folder_items[item_id]
                item = items_by_id.get(item_id)
                if item is None:
                    is_new = True
                    item = QtGui.QStandardItem()
                    item.setEditable(False)
                else:
                    is_new = self._parent_id_by_id[item_id] != parent_id

                self._fill_item_data(item, folder_item)
                if is_new:
                    new_items.append(item)
                self._items_by_id[item_id] = item
                self._parent_id_by_id[item_id] = parent_id

                hierarchy_queue.append((item, item_id))

            if new_items:
                parent_item.appendRows(new_items)

        for item_id in ids_to_remove:
            self._items_by_id.pop(item_id)
            self._parent_id_by_id.pop(item_id)

        self._is_refreshing = False
        self.refreshed.emit()


class FoldersWidget(QtWidgets.QWidget):
    """Folders widget.

    Widget that handles folders view, model and selection.

    Expected selection handling is disabled by default. If enabled, the
    widget will handle the expected in predefined way. Widget is listening
    to event 'expected_selection_changed' with expected event data below,
    the same data must be available when called method
    'get_expected_selection_data' on controller.

    {
        "folder": {
            "current": bool,               # Folder is what should be set now
            "folder_id": Union[str, None], # Folder id that should be selected
        },
        ...
    }

    Selection is confirmed by calling method 'expected_folder_selected' on
    controller.


    Args:
        controller (AbstractWorkfilesFrontend): The control object.
        parent (QtWidgets.QWidget): The parent widget.
        handle_expected_selection (bool): If True, the widget will handle
            the expected selection. Defaults to False.
    """

    double_clicked = QtCore.Signal(QtGui.QMouseEvent)
    selection_changed = QtCore.Signal()
    refreshed = QtCore.Signal()

    def __init__(self, controller, parent, handle_expected_selection=False):
        super(FoldersWidget, self).__init__(parent)

        folders_view = TreeView(self)
        folders_view.setHeaderHidden(True)

        folders_model = FoldersQtModel(controller)
        folders_proxy_model = RecursiveSortFilterProxyModel()
        folders_proxy_model.setSourceModel(folders_model)
        folders_proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        folders_view.setModel(folders_proxy_model)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(folders_view, 1)

        controller.register_event_callback(
            "selection.project.changed",
            self._on_project_selection_change,
        )
        controller.register_event_callback(
            "folders.refresh.finished",
            self._on_folders_refresh_finished
        )
        controller.register_event_callback(
            "controller.refresh.finished",
            self._on_controller_refresh
        )
        controller.register_event_callback(
            "expected_selection_changed",
            self._on_expected_selection_change
        )

        selection_model = folders_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)
        folders_view.double_clicked.connect(self.double_clicked)
        folders_model.refreshed.connect(self._on_model_refresh)

        self._controller = controller
        self._folders_view = folders_view
        self._folders_model = folders_model
        self._folders_proxy_model = folders_proxy_model

        self._handle_expected_selection = handle_expected_selection
        self._expected_selection = None

    @property
    def is_refreshing(self):
        """Model is refreshing.

        Returns:
            bool: True if model is refreshing.
        """

        return self._folders_model.is_refreshing

    @property
    def has_content(self):
        """Has at least one folder.

        Returns:
            bool: True if model has at least one folder.
        """

        return self._folders_model.has_content

    def set_name_filter(self, name):
        """Set filter of folder name.

        Args:
            name (str): The string filter.
        """

        self._folders_proxy_model.setFilterFixedString(name)

    def refresh(self):
        """Refresh folders model.

        Force to update folders model from controller.
        """

        self._folders_model.refresh()

    def get_project_name(self):
        """Project name in which folders widget currently is.

        Returns:
            Union[str, None]: Currently used project name.
        """

        return self._folders_model.get_project_name()

    def set_project_name(self, project_name):
        """Set project name.

        Do not use this method when controller is handling selection of
        project using 'selection.project.changed' event.

        Args:
            project_name (str): Project name.
        """

        self._folders_model.set_project_name(project_name)

    def get_selected_folder_id(self):
        """Get selected folder id.

        Returns:
            Union[str, None]: Folder id which is selected.
        """

        return self._get_selected_item_id()

    def get_selected_folder_label(self):
        """Selected folder label.

        Returns:
            Union[str, None]: Selected folder label.
        """

        item_id = self._get_selected_item_id()
        return self.get_folder_label(item_id)

    def get_folder_label(self, folder_id):
        """Folder label for a given folder id.

        Returns:
            Union[str, None]: Folder label.
        """

        index = self._folders_model.get_index_by_id(folder_id)
        if index.isValid():
            return index.data(QtCore.Qt.DisplayRole)
        return None

    def set_selected_folder(self, folder_id):
        """Change selection.

        Args:
            folder_id (Union[str, None]): Folder id or None to deselect.
        """

        if folder_id is None:
            self._folders_view.clearSelection()
            return True

        if folder_id == self._get_selected_item_id():
            return True
        index = self._folders_model.get_index_by_id(folder_id)
        if not index.isValid():
            return False

        proxy_index = self._folders_proxy_model.mapFromSource(index)
        if not proxy_index.isValid():
            return False

        selection_model = self._folders_view.selectionModel()
        selection_model.setCurrentIndex(
            proxy_index, QtCore.QItemSelectionModel.SelectCurrent
        )
        return True

    def set_deselectable(self, enabled):
        """Set deselectable mode.

        Items in view can be deselected.

        Args:
            enabled (bool): Enable deselectable mode.
        """

        self._folders_view.set_deselectable(enabled)

    def _get_selected_index(self):
        return self._folders_model.get_index_by_id(
            self.get_selected_folder_id()
        )

    def _on_project_selection_change(self, event):
        project_name = event["project_name"]
        self.set_project_name(project_name)

    def _on_folders_refresh_finished(self, event):
        if event["sender"] != FOLDERS_MODEL_SENDER_NAME:
            self.set_project_name(event["project_name"])

    def _on_controller_refresh(self):
        self._update_expected_selection()

    def _on_model_refresh(self):
        if self._expected_selection:
            self._set_expected_selection()
        self._folders_proxy_model.sort(0)
        self.refreshed.emit()

    def _get_selected_item_id(self):
        selection_model = self._folders_view.selectionModel()
        for index in selection_model.selectedIndexes():
            item_id = index.data(FOLDER_ID_ROLE)
            if item_id is not None:
                return item_id
        return None

    def _on_selection_change(self):
        item_id = self._get_selected_item_id()
        self._controller.set_selected_folder(item_id)
        self.selection_changed.emit()

    # Expected selection handling
    def _on_expected_selection_change(self, event):
        self._update_expected_selection(event.data)

    def _update_expected_selection(self, expected_data=None):
        if not self._handle_expected_selection:
            return

        if expected_data is None:
            expected_data = self._controller.get_expected_selection_data()

        folder_data = expected_data.get("folder")
        if not folder_data or not folder_data["current"]:
            return

        folder_id = folder_data["id"]
        self._expected_selection = folder_id
        if not self._folders_model.is_refreshing:
            self._set_expected_selection()

    def _set_expected_selection(self):
        if not self._handle_expected_selection:
            return

        folder_id = self._expected_selection
        self._expected_selection = None
        if folder_id is not None:
            self.set_selected_folder(folder_id)
        self._controller.expected_folder_selected(folder_id)
