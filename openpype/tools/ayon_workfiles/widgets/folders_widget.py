import uuid
import collections

import qtawesome
from qtpy import QtWidgets, QtGui, QtCore

from openpype.tools.utils import (
    RecursiveSortFilterProxyModel,
    DeselectableTreeView,
)

from .constants import ITEM_ID_ROLE, ITEM_NAME_ROLE

SENDER_NAME = "qt_folders_model"


class RefreshThread(QtCore.QThread):
    refresh_finished = QtCore.Signal(str)

    def __init__(self, controller):
        super(RefreshThread, self).__init__()
        self._id = uuid.uuid4().hex
        self._controller = controller
        self._result = None

    @property
    def id(self):
        return self._id

    def run(self):
        self._result = self._controller.get_folder_items(SENDER_NAME)
        self.refresh_finished.emit(self.id)

    def get_result(self):
        return self._result


class FoldersModel(QtGui.QStandardItemModel):
    refreshed = QtCore.Signal()

    def __init__(self, controller):
        super(FoldersModel, self).__init__()

        self._controller = controller
        self._items_by_id = {}
        self._parent_id_by_id = {}

        self._refresh_threads = {}
        self._current_refresh_thread = None

        self._has_content = False
        self._is_refreshing = False

    @property
    def is_refreshing(self):
        return self._is_refreshing

    @property
    def has_content(self):
        return self._has_content

    def clear(self):
        self._items_by_id = {}
        self._parent_id_by_id = {}
        self._has_content = False
        super(FoldersModel, self).clear()

    def get_index_by_id(self, item_id):
        item = self._items_by_id.get(item_id)
        if item is None:
            return QtCore.QModelIndex()
        return self.indexFromItem(item)

    def refresh(self):
        self._is_refreshing = True

        thread = RefreshThread(self._controller)
        self._current_refresh_thread = thread.id
        self._refresh_threads[thread.id] = thread
        thread.refresh_finished.connect(self._on_refresh_thread)
        thread.start()

    def _on_refresh_thread(self, thread_id):
        thread = self._refresh_threads.pop(thread_id)
        if thread_id != self._current_refresh_thread:
            return

        folder_items_by_id = thread.get_result()
        if not folder_items_by_id:
            if folder_items_by_id is not None:
                self.clear()
            self._is_refreshing = False
            return

        self._has_content = True

        folder_ids = set(folder_items_by_id)
        ids_to_remove = set(self._items_by_id) - folder_ids

        folder_items_by_parent = collections.defaultdict(list)
        for folder_item in folder_items_by_id.values():
            folder_items_by_parent[folder_item.parent_id].append(folder_item)

        hierarchy_queue = collections.deque()
        hierarchy_queue.append(None)

        while hierarchy_queue:
            parent_id = hierarchy_queue.popleft()
            folder_items = folder_items_by_parent[parent_id]
            if parent_id is None:
                parent_item = self.invisibleRootItem()
            else:
                parent_item = self._items_by_id[parent_id]

            new_items = []
            for folder_item in folder_items:
                item_id = folder_item.entity_id
                item = self._items_by_id.get(item_id)
                if item is None:
                    is_new = True
                    item = QtGui.QStandardItem()
                    item.setEditable(False)
                else:
                    is_new = self._parent_id_by_id[item_id] != parent_id

                icon = qtawesome.icon(
                    folder_item.icon_name,
                    color=folder_item.icon_color,
                )
                item.setData(item_id, ITEM_ID_ROLE)
                item.setData(folder_item.name, ITEM_NAME_ROLE)
                item.setData(folder_item.label, QtCore.Qt.DisplayRole)
                item.setData(icon, QtCore.Qt.DecorationRole)
                if is_new:
                    new_items.append(item)
                self._items_by_id[item_id] = item
                self._parent_id_by_id[item_id] = parent_id

                hierarchy_queue.append(item_id)

            if new_items:
                parent_item.appendRows(new_items)

        for item_id in ids_to_remove:
            item = self._items_by_id[item_id]
            parent_id = self._parent_id_by_id[item_id]
            if parent_id is None:
                parent_item = self.invisibleRootItem()
            else:
                parent_item = self._items_by_id[parent_id]
            parent_item.takeChild(item.row())

        for item_id in ids_to_remove:
            self._items_by_id.pop(item_id)
            self._parent_id_by_id.pop(item_id)

        self._is_refreshing = False
        self.refreshed.emit()


class FoldersWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(FoldersWidget, self).__init__(parent)

        folders_view = DeselectableTreeView(self)
        folders_view.setHeaderHidden(True)

        folders_model = FoldersModel(controller)
        folders_proxy_model = RecursiveSortFilterProxyModel()
        folders_proxy_model.setSourceModel(folders_model)

        folders_view.setModel(folders_proxy_model)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(folders_view, 1)

        controller.register_event_callback(
            "folders.refresh.started",
            self._on_folders_refresh_started
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

        folders_model.refreshed.connect(self._on_model_refresh)

        self._controller = controller
        self._folders_view = folders_view
        self._folders_model = folders_model
        self._folders_proxy_model = folders_proxy_model

        self._last_project = None

        self._expected_selection = None

    def set_name_filer(self, name):
        self._folders_proxy_model.setFilterFixedString(name)

    def _clear(self):
        self._folders_model.clear()

    def _on_folders_refresh_started(self, event):
        if self._last_project != event["project_name"]:
            self._clear()

    def _on_folders_refresh_finished(self, event):
        if event["sender"] != SENDER_NAME:
            self._folders_model.refresh()

    def _on_controller_refresh(self):
        self._update_expected_selection()

    def _update_expected_selection(self, expected_data=None):
        if expected_data is None:
            expected_data = self._controller.get_expected_selection_data()

        # We're done
        if expected_data["folder_selected"]:
            return

        folder_id = expected_data["folder_id"]
        self._expected_selection = folder_id
        if not self._folders_model.is_refreshing:
            self._set_expected_selection()

    def _set_expected_selection(self):
        folder_id = self._expected_selection
        self._expected_selection = None
        if (
            folder_id is not None
            and folder_id != self._get_selected_item_id()
        ):
            index = self._folders_model.get_index_by_id(folder_id)
            if index.isValid():
                proxy_index = self._folders_proxy_model.mapFromSource(index)
                self._folders_view.setCurrentIndex(proxy_index)
        self._controller.expected_folder_selected(folder_id)

    def _on_model_refresh(self):
        if self._expected_selection:
            self._set_expected_selection()
        self._folders_proxy_model.sort(0)

    def _on_expected_selection_change(self, event):
        self._update_expected_selection(event.data)

    def _get_selected_item_id(self):
        selection_model = self._folders_view.selectionModel()
        for index in selection_model.selectedIndexes():
            item_id = index.data(ITEM_ID_ROLE)
            if item_id is not None:
                return item_id
        return None

    def _on_selection_change(self):
        item_id = self._get_selected_item_id()
        self._controller.set_selected_folder(item_id)
