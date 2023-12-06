import collections

from qtpy import QtWidgets, QtGui, QtCore
import qtawesome

from openpype.style import get_default_entity_icon_color
from openpype.tools.ayon_utils.widgets import get_qt_icon
from openpype.tools.utils import DeselectableTreeView

from .actions_utils import show_actions_menu

REPRESENTAION_NAME_ROLE = QtCore.Qt.UserRole + 1
REPRESENTATION_ID_ROLE = QtCore.Qt.UserRole + 2
PRODUCT_NAME_ROLE = QtCore.Qt.UserRole + 3
FOLDER_LABEL_ROLE = QtCore.Qt.UserRole + 4
GROUP_TYPE_ROLE = QtCore.Qt.UserRole + 5
ACTIVE_SITE_ICON_ROLE = QtCore.Qt.UserRole + 6
REMOTE_SITE_ICON_ROLE = QtCore.Qt.UserRole + 7
SYNC_ACTIVE_SITE_PROGRESS = QtCore.Qt.UserRole + 8
SYNC_REMOTE_SITE_PROGRESS = QtCore.Qt.UserRole + 9


class RepresentationsModel(QtGui.QStandardItemModel):
    refreshed = QtCore.Signal()
    colums_info = [
        ("Name", 120),
        ("Product name", 125),
        ("Folder", 125),
        ("Active site", 85),
        ("Remote site", 85)
    ]
    column_labels = [label for label, _ in colums_info]
    column_widths = [width for _, width in colums_info]
    folder_column = column_labels.index("Product name")
    active_site_column = column_labels.index("Active site")
    remote_site_column = column_labels.index("Remote site")

    def __init__(self, controller):
        super(RepresentationsModel, self).__init__()

        self.setColumnCount(len(self.column_labels))

        for idx, label in enumerate(self.column_labels):
            self.setHeaderData(idx, QtCore.Qt.Horizontal, label)

        controller.register_event_callback(
            "selection.project.changed",
            self._on_project_change
        )
        controller.register_event_callback(
            "selection.versions.changed",
            self._on_version_change
        )
        self._selected_project_name = None
        self._selected_version_ids = None

        self._group_icon = None

        self._items_by_id = {}
        self._groups_items_by_name = {}

        self._controller = controller

    def refresh(self):
        repre_items = self._controller.get_representation_items(
            self._selected_project_name, self._selected_version_ids
        )
        self._fill_items(repre_items, self._selected_project_name)
        self.refreshed.emit()

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        col = index.column()
        if col != 0:
            if role == QtCore.Qt.DecorationRole:
                if col == 3:
                    role = ACTIVE_SITE_ICON_ROLE
                elif col == 4:
                    role = REMOTE_SITE_ICON_ROLE
                else:
                    return None

            if role == QtCore.Qt.DisplayRole:
                if col == 1:
                    role = PRODUCT_NAME_ROLE
                elif col == 2:
                    role = FOLDER_LABEL_ROLE
                elif col == 3:
                    role = SYNC_ACTIVE_SITE_PROGRESS
                elif col == 4:
                    role = SYNC_REMOTE_SITE_PROGRESS

            index = self.index(index.row(), 0, index.parent())
        return super(RepresentationsModel, self).data(index, role)

    def setData(self, index, value, role=None):
        if role is None:
            role = QtCore.Qt.EditRole
        return super(RepresentationsModel, self).setData(index, value, role)

    def _clear_items(self):
        self._items_by_id = {}
        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())

    def _get_repre_item(
        self,
        repre_item,
        active_site_icon,
        remote_site_icon,
        repres_sync_status
    ):
        repre_id = repre_item.representation_id
        repre_name = repre_item.representation_name
        repre_icon = repre_item.representation_icon
        item = self._items_by_id.get(repre_id)
        is_new_item = False
        if item is None:
            is_new_item = True
            item = QtGui.QStandardItem()
            self._items_by_id[repre_id] = item
            item.setColumnCount(self.columnCount())
            item.setEditable(False)

        sync_status = repres_sync_status[repre_id]
        active_progress, remote_progress = sync_status

        active_site_progress = "{}%".format(int(active_progress * 100))
        remote_site_progress = "{}%".format(int(remote_progress * 100))

        icon = get_qt_icon(repre_icon)
        item.setData(repre_name, QtCore.Qt.DisplayRole)
        item.setData(icon, QtCore.Qt.DecorationRole)
        item.setData(repre_name, REPRESENTAION_NAME_ROLE)
        item.setData(repre_id, REPRESENTATION_ID_ROLE)
        item.setData(repre_item.product_name, PRODUCT_NAME_ROLE)
        item.setData(repre_item.folder_label, FOLDER_LABEL_ROLE)
        item.setData(active_site_icon, ACTIVE_SITE_ICON_ROLE)
        item.setData(remote_site_icon, REMOTE_SITE_ICON_ROLE)
        item.setData(active_site_progress, SYNC_ACTIVE_SITE_PROGRESS)
        item.setData(remote_site_progress, SYNC_REMOTE_SITE_PROGRESS)
        return is_new_item, item

    def _get_group_icon(self):
        if self._group_icon is None:
            self._group_icon = qtawesome.icon(
                "fa.folder",
                color=get_default_entity_icon_color()
            )
        return self._group_icon

    def _get_group_item(self, repre_name):
        item = self._groups_items_by_name.get(repre_name)
        if item is not None:
            return False, item

        # TODO add color
        item = QtGui.QStandardItem()
        item.setColumnCount(self.columnCount())
        item.setData(repre_name, QtCore.Qt.DisplayRole)
        item.setData(self._get_group_icon(), QtCore.Qt.DecorationRole)
        item.setData(0, GROUP_TYPE_ROLE)
        item.setEditable(False)
        self._groups_items_by_name[repre_name] = item
        return True, item

    def _fill_items(self, repre_items, project_name):
        active_site_icon_def = self._controller.get_active_site_icon_def(
            project_name
        )
        remote_site_icon_def = self._controller.get_remote_site_icon_def(
            project_name
        )
        active_site_icon = get_qt_icon(active_site_icon_def)
        remote_site_icon = get_qt_icon(remote_site_icon_def)

        items_to_remove = set(self._items_by_id.keys())
        repre_items_by_name = collections.defaultdict(list)
        repre_ids = set()
        for repre_item in repre_items:
            repre_ids.add(repre_item.representation_id)
            items_to_remove.discard(repre_item.representation_id)
            repre_name = repre_item.representation_name
            repre_items_by_name[repre_name].append(repre_item)

        repres_sync_status = self._controller.get_representations_sync_status(
            project_name, repre_ids
        )

        root_item = self.invisibleRootItem()
        for repre_id in items_to_remove:
            item = self._items_by_id.pop(repre_id)
            parent_item = item.parent()
            if parent_item is None:
                parent_item = root_item
            parent_item.removeRow(item.row())

        group_names = set()
        new_root_items = []
        for repre_name, repre_name_items in repre_items_by_name.items():
            group_item = None
            parent_is_group = False
            if len(repre_name_items) > 1:
                group_names.add(repre_name)
                is_new_group, group_item = self._get_group_item(repre_name)
                if is_new_group:
                    new_root_items.append(group_item)
                parent_is_group = True

            new_group_items = []
            for repre_item in repre_name_items:
                is_new_item, item = self._get_repre_item(
                    repre_item,
                    active_site_icon,
                    remote_site_icon,
                    repres_sync_status
                )
                item_parent = item.parent()
                if item_parent is None:
                    item_parent = root_item

                if not is_new_item:
                    if parent_is_group:
                        if item_parent is group_item:
                            continue
                    elif item_parent is root_item:
                        continue
                    item_parent.takeRow(item.row())
                    is_new_item = True

                if is_new_item:
                    new_group_items.append(item)

            if not new_group_items:
                continue

            if group_item is not None:
                group_item.appendRows(new_group_items)
            else:
                new_root_items.extend(new_group_items)

        if new_root_items:
            root_item.appendRows(new_root_items)

        for group_name in set(self._groups_items_by_name) - group_names:
            item = self._groups_items_by_name.pop(group_name)
            parent_item = item.parent()
            if parent_item is None:
                parent_item = root_item
            parent_item.removeRow(item.row())

    def _on_project_change(self, event):
        self._selected_project_name = event["project_name"]

    def _on_version_change(self, event):
        self._selected_version_ids = event["version_ids"]
        self.refresh()


class RepresentationsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(RepresentationsWidget, self).__init__(parent)

        repre_view = DeselectableTreeView(self)
        repre_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        repre_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        repre_view.setSortingEnabled(True)
        repre_view.setAlternatingRowColors(True)

        repre_model = RepresentationsModel(controller)
        repre_proxy_model = QtCore.QSortFilterProxyModel()
        repre_proxy_model.setSourceModel(repre_model)
        repre_proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        repre_view.setModel(repre_proxy_model)

        for idx, width in enumerate(repre_model.column_widths):
            repre_view.setColumnWidth(idx, width)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(repre_view, 1)

        repre_view.customContextMenuRequested.connect(
            self._on_context_menu)
        repre_view.selectionModel().selectionChanged.connect(
            self._on_selection_change)
        repre_model.refreshed.connect(self._on_model_refresh)

        controller.register_event_callback(
            "selection.project.changed",
            self._on_project_change
        )
        controller.register_event_callback(
            "selection.folders.changed",
            self._on_folder_change
        )

        self._controller = controller
        self._selected_project_name = None
        self._selected_multiple_folders = None

        self._repre_view = repre_view
        self._repre_model = repre_model
        self._repre_proxy_model = repre_proxy_model

        self._set_site_sync_visibility(
            self._controller.is_site_sync_enabled()
        )
        self._set_multiple_folders_selected(False)

    def refresh(self):
        self._repre_model.refresh()

    def _on_folder_change(self, event):
        self._set_multiple_folders_selected(len(event["folder_ids"]) > 1)

    def _on_project_change(self, event):
        self._selected_project_name = event["project_name"]
        site_sync_enabled = self._controller.is_site_sync_enabled(
            self._selected_project_name
        )
        self._set_site_sync_visibility(site_sync_enabled)

    def _set_site_sync_visibility(self, site_sync_enabled):
        self._repre_view.setColumnHidden(
            self._repre_model.active_site_column,
            not site_sync_enabled
        )
        self._repre_view.setColumnHidden(
            self._repre_model.remote_site_column,
            not site_sync_enabled
        )

    def _set_multiple_folders_selected(self, selected_multiple_folders):
        if selected_multiple_folders == self._selected_multiple_folders:
            return
        self._selected_multiple_folders = selected_multiple_folders
        self._repre_view.setColumnHidden(
            self._repre_model.folder_column,
            not self._selected_multiple_folders
        )

    def _on_model_refresh(self):
        self._repre_proxy_model.sort(0)

    def _get_selected_repre_indexes(self):
        selection_model = self._repre_view.selectionModel()
        model = self._repre_view.model()
        indexes_queue = collections.deque()
        indexes_queue.extend(selection_model.selectedIndexes())

        selected_indexes = []
        while indexes_queue:
            index = indexes_queue.popleft()
            if index.column() != 0:
                continue

            group_type = model.data(index, GROUP_TYPE_ROLE)
            if group_type is None:
                selected_indexes.append(index)

            elif group_type == 0:
                for row in range(model.rowCount(index)):
                    child_index = model.index(row, 0, index)
                    indexes_queue.append(child_index)

        return selected_indexes

    def _get_selected_repre_ids(self):
        repre_ids = {
            index.data(REPRESENTATION_ID_ROLE)
            for index in self._get_selected_repre_indexes()
        }
        repre_ids.discard(None)
        return repre_ids

    def _on_selection_change(self):
        selected_repre_ids = self._get_selected_repre_ids()
        self._controller.set_selected_representations(selected_repre_ids)

    def _on_context_menu(self, point):
        repre_ids = self._get_selected_repre_ids()
        action_items = self._controller.get_representations_action_items(
            self._selected_project_name, repre_ids
        )
        global_point = self._repre_view.mapToGlobal(point)
        result = show_actions_menu(
            action_items,
            global_point,
            len(repre_ids) == 1,
            self
        )
        action_item, options = result
        if action_item is None or options is None:
            return

        self._controller.trigger_action_item(
            action_item.identifier,
            options,
            action_item.project_name,
            version_ids=action_item.version_ids,
            representation_ids=action_item.representation_ids,
        )
