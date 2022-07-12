import collections
from Qt import QtWidgets, QtCore, QtGui

from openpype.tools.utils import RecursiveSortFilterProxyModel

UNIQUE_ID_ROLE = QtCore.Qt.UserRole + 1


class ContainersWidget(QtWidgets.QTreeView):
    def __init__(self, controller, parent):
        super(ContainersWidget, self).__init__(parent)

        self.setHeaderHidden(True)

        containers_model = QtGui.QStandardItemModel()
        proxy_model = RecursiveSortFilterProxyModel()
        proxy_model.setSourceModel(containers_model)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setModel(proxy_model)

        self._controller = controller

        self._containers_model = containers_model
        self._proxy_model = proxy_model

        self._items_by_id = {}
        self._parent_id_by_item_id = {}
        self._item_ids_by_parent_id = collections.defaultdict(set)

    def set_subset_name_filter(self, subset_name):
        self._proxy_model.setFilterFixedString(subset_name)

    def _make_sure_group_exists(self, container_group):
        group_id = container_group.id
        group_item = self._items_by_id.get(group_id)
        add_to_parent = False
        if group_item is None:
            add_to_parent = True
            group_item = QtGui.QStandardItem()
            group_item.setData(group_id, UNIQUE_ID_ROLE)
            self._items_by_id[group_id] = group_item
            self._parent_id_by_item_id[group_id] = None
            self._item_ids_by_parent_id[None].add(group_id)

        for value, role in (
            (container_group.label, QtCore.Qt.DisplayRole),
        ):
            if group_item.data(role) != value:
                group_item.setData(value, role)

        flags = QtCore.Qt.ItemIsEnabled
        if container_group.is_valid:
            flags |= QtCore.Qt.ItemIsSelectable
        group_item.setFlags(flags)
        return group_item, add_to_parent

    def _make_sure_container_exists(self, container_item, group_id):
        item_id = container_item.id
        item = self._items_by_id.get(item_id)
        add_to_parent = False
        if item is None:
            item = QtGui.QStandardItem()
            item.setData(item_id, UNIQUE_ID_ROLE)

            self._items_by_id[item_id] = item
            self._parent_id_by_item_id[item_id] = group_id
            self._item_ids_by_parent_id[group_id].add(item_id)
            add_to_parent = True

        parent_id = self._parent_id_by_item_id[item_id]
        if parent_id != group_id:
            add_to_parent = True
            previous_parent_item = self._items_by_id[parent_id]
            previous_parent_item.takeRow(item.row())
            self._item_ids_by_parent_id[parent_id].remove(item_id)
            self._item_ids_by_parent_id[group_id].add(item_id)

        for value, role in (
            (container_item.label, QtCore.Qt.DisplayRole),
        ):
            if item.data(role) != value:
                item.setData(value, role)

        flags = QtCore.Qt.ItemIsEnabled
        if container_item.is_valid:
            flags |= QtCore.Qt.ItemIsSelectable
        item.setFlags(flags)
        return item, add_to_parent

    def refresh_model(self):
        new_group_items = []
        item_ids_to_remove = set(self._items_by_id.keys())
        container_groups = self._controller.get_container_groups()
        for container_group in container_groups:
            group_id = container_group.id
            if group_id in item_ids_to_remove:
                item_ids_to_remove.remove(group_id)

            group_item, add_to_parent = (
                self._make_sure_group_exists(container_group)
            )
            if add_to_parent:
                new_group_items.append(group_item)

            new_items_in_group = []
            for container_item in container_group.containers:
                item_id = container_item.id
                if item_id in item_ids_to_remove:
                    item_ids_to_remove.remove(item_id)

                item, add_to_parent = self._make_sure_container_exists(
                    container_item, group_id
                )
                if add_to_parent:
                    new_items_in_group.append(item)

            if new_items_in_group:
                group_item.appendRows(new_items_in_group)

        # Add new group items
        root_item = self._containers_model.invisibleRootItem()
        if new_group_items:
            root_item.appendRows(new_group_items)

        # Remove missing items
        to_remove_queue = collections.deque(item_ids_to_remove)
        while to_remove_queue:
            item_id = to_remove_queue.popleft()
            children_in_process = False
            for child_id in self._item_ids_by_parent_id[item_id]:
                children_in_process = True
                if child_id not in to_remove_queue:
                    to_remove_queue.append(child_id)

            if children_in_process:
                to_remove_queue.append(item_id)
                continue

            item = self._items_by_id.pop(item_id)
            parent_id = self._parent_id_by_item_id.pop(item_id)
            self._item_ids_by_parent_id[parent_id].remove(item_id)
            self._item_ids_by_parent_id.pop(item_id, None)
            if parent_id is None:
                parent_item = root_item
            else:
                parent_item = self._items_by_id[parent_id]
            parent_item.removeRow(item.row())


class FamiliesWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(FamiliesWidget, self).__init__(parent)

        families_view = QtWidgets.QListView(self)
        families_model = QtGui.QStandardItemModel()
        families_view.setModel(families_model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(families_view, 1)

        self._families_model = families_model
        self._families_view = families_view


class VersionsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(VersionsWidget, self).__init__(parent)

        versions_view = QtWidgets.QTreeView(self)
        versions_model = QtGui.QStandardItemModel()
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(versions_model)
        versions_view.setModel(proxy_model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(versions_view, 1)

        self._versions_view = versions_view
        self._versions_model = versions_model
        self._proxy_model = proxy_model


class ThumbnailsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ThumbnailsWidget, self).__init__(parent)

        thumbnail_label = QtWidgets.QLabel("Thumbnail", self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(thumbnail_label, 1)


class VersionsInformationWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(VersionsInformationWidget, self).__init__(parent)

        version_label = QtWidgets.QLabel("Version info", self)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(version_label, 1)