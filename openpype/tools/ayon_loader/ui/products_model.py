import collections
from qtpy import QtGui, QtCore

from openpype.tools.ayon_utils.widgets import get_qt_icon

PRODUCTS_MODEL_SENDER_NAME = "qt_products_model"

FOLDER_LABEL_ROLE = QtCore.Qt.UserRole + 2
FOLDER_ID_ROLE = QtCore.Qt.UserRole + 3
PRODUCT_ID_ROLE = QtCore.Qt.UserRole + 5
PRODUCT_NAME_ROLE = QtCore.Qt.UserRole + 6
PRODUCT_TYPE_ROLE = QtCore.Qt.UserRole + 7
PRODUCT_TYPE_ICON_ROLE = QtCore.Qt.UserRole + 8
VERSION_ID_ROLE = QtCore.Qt.UserRole + 9
VERSION_HERO_ROLE = QtCore.Qt.UserRole + 10
VERSION_NAME_ROLE = QtCore.Qt.UserRole + 11
VERSION_NAME_EDIT_ROLE = QtCore.Qt.UserRole + 12
VERSION_PUBLISH_TIME_ROLE = QtCore.Qt.UserRole + 13
VERSION_AUTHOR_ROLE = QtCore.Qt.UserRole + 14
VERSION_FRAME_RANGE_ROLE = QtCore.Qt.UserRole + 15
VERSION_DURATION_ROLE = QtCore.Qt.UserRole + 16
VERSION_HANDLES_ROLE = QtCore.Qt.UserRole + 17
VERSION_STEP_ROLE = QtCore.Qt.UserRole + 18
VERSION_IN_SCENE_ROLE = QtCore.Qt.UserRole + 19
VERSION_AVAILABLE_ROLE = QtCore.Qt.UserRole + 20


class ProductsModel(QtGui.QStandardItemModel):
    column_labels = [
        "Product name",
        "Product type",
        "Folder",
        "Version",
        "Time",
        "Author",
        "Frames",
        "Duration",
        "Handles",
        "Step",
        "In scene",
        "Availability",
    ]

    version_col = column_labels.index("Version")
    published_time_col = column_labels.index("Time")
    folders_label_col = column_labels.index("Folder")

    def __init__(self, controller):
        super(ProductsModel, self).__init__()
        self.setColumnCount(len(self.column_labels))
        for idx, label in enumerate(self.column_labels):
            self.setHeaderData(idx, QtCore.Qt.Horizontal, label)
        self._controller = controller

        # Variables to store 'QStandardItem'
        self._items_by_id = {}
        self._group_items_by_name = {}
        self._merged_items_by_id = {}

        # product item objects (they have version information)
        self._product_items_by_id = {}
        self._grouping_enabled = False

    def flags(self, index):
        # Make the version column editable
        if index.column() == self.version_col and index.data(PRODUCT_ID_ROLE):
            return (
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsEditable
            )
        if index.column() != 0:
            index = self.index(index.row(), 0, index.parent())
        return super(ProductsModel, self).flags(index)

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        if not index.isValid():
            return None

        col = index.column()
        if col == 0:
            return super(ProductsModel, self).data(index, role)

        if role == QtCore.Qt.DecorationRole:
            if col == 1:
                role = PRODUCT_TYPE_ICON_ROLE
            else:
                return None

        if (
            role == VERSION_NAME_EDIT_ROLE
            or (role == QtCore.Qt.EditRole and col == self.version_col)
        ):
            index = self.index(index.row(), 0, index.parent())
            product_id = index.data(PRODUCT_ID_ROLE)
            product_item = self._product_items_by_id.get(product_id)
            if product_item is None:
                return None
            return product_item.versions

        if role == QtCore.Qt.EditRole:
            return None

        if role == QtCore.Qt.DisplayRole:
            if not index.data(PRODUCT_ID_ROLE):
                return None
            if col == self.version_col:
                role = VERSION_NAME_ROLE
            elif col == 1:
                role = PRODUCT_TYPE_ROLE
            elif col == 2:
                role = FOLDER_LABEL_ROLE
            elif col == 4:
                role = VERSION_PUBLISH_TIME_ROLE
            elif col == 5:
                role = VERSION_AUTHOR_ROLE
            elif col == 6:
                role = VERSION_FRAME_RANGE_ROLE
            elif col == 7:
                role = VERSION_DURATION_ROLE
            elif col == 8:
                role = VERSION_HANDLES_ROLE
            elif col == 9:
                role = VERSION_STEP_ROLE
            elif col == 10:
                role = VERSION_IN_SCENE_ROLE
            elif col == 11:
                role = VERSION_AVAILABLE_ROLE
            else:
                return None

        index = self.index(index.row(), 0, index.parent())

        return super(ProductsModel, self).data(index, role)

    def setData(self, index, value, role=None):
        if not index.isValid():
            return False

        if role is None:
            role = QtCore.Qt.EditRole

        col = index.column()
        if col == self.version_col and role == QtCore.Qt.EditRole:
            role = VERSION_NAME_EDIT_ROLE

        if role == VERSION_NAME_EDIT_ROLE:
            if col != 0:
                index = self.index(index.row(), 0, index.parent())
            product_id = index.data(PRODUCT_ID_ROLE)
            product_item = self._product_items_by_id[product_id]
            version_item = product_item.get_version_by_id(value)
            if version_item is None:
                return False
            if index.data(VERSION_ID_ROLE) == version_item.version_id:
                return True
            item = self.itemFromIndex(index)
            self._set_version_data_to_product_item(item, version_item)
            return True
        return super(ProductsModel, self).setData(index, value, role)

    def _clear(self):
        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())

        self._items_by_id = {}
        self._group_items_by_name = {}
        self._merged_items_by_id = {}

        self._product_items_by_id = {}

    def _get_group_model_item(self, group_name):
        model_item = self._group_items_by_name.get(group_name)
        if model_item is None:
            model_item = QtGui.QStandardItem(group_name)
            model_item.setEditable(False)
            model_item.setColumnCount(self.columnCount())
            self._group_items_by_name[group_name] = model_item
        return model_item

    def _get_merged_model_item(self, path):
        model_item = self._merged_items_by_id.get(path)
        if model_item is None:
            model_item = QtGui.QStandardItem(path)
            model_item.setEditable(False)
            model_item.setColumnCount(self.columnCount())
            self._merged_items_by_id[path] = model_item
        return model_item

    def _set_version_data_to_product_item(self, model_item, version_item):
        """

        Args:
            model_item (QtGui.QStandardItem): Item which should have values
                from version item.
            version_item (VersionItem): Item from entities model with
                information about version.
        """

        model_item.setData(version_item.version_id, VERSION_ID_ROLE)
        model_item.setData(version_item.version, VERSION_NAME_ROLE)
        model_item.setData(version_item.version_id, VERSION_ID_ROLE)
        model_item.setData(version_item.is_hero, VERSION_HERO_ROLE)
        model_item.setData(
            version_item.published_time, VERSION_PUBLISH_TIME_ROLE
        )
        model_item.setData(version_item.author, VERSION_AUTHOR_ROLE)
        model_item.setData(version_item.frame_range, VERSION_FRAME_RANGE_ROLE)
        model_item.setData(version_item.duration, VERSION_DURATION_ROLE)
        model_item.setData(version_item.handles, VERSION_HANDLES_ROLE)
        model_item.setData(version_item.step, VERSION_STEP_ROLE)
        model_item.setData(version_item.in_scene, VERSION_IN_SCENE_ROLE)

    def _get_product_model_item(self, product_item):
        model_item = self._items_by_id.get(product_item.product_id)
        versions = list(product_item.version_items)
        versions.sort()
        last_version = versions[-1]
        if model_item is None:
            product_id = product_item.product_id
            model_item = QtGui.QStandardItem(product_item.product_name)
            model_item.setEditable(False)
            icon = get_qt_icon(product_item.product_icon)
            product_type_icon = get_qt_icon(product_item.product_type_icon)
            model_item.setColumnCount(self.columnCount())
            model_item.setData(icon, QtCore.Qt.DecorationRole)
            model_item.setData(product_id, PRODUCT_ID_ROLE)
            model_item.setData(product_item.product_name, PRODUCT_NAME_ROLE)
            model_item.setData(product_item.product_type, PRODUCT_TYPE_ROLE)
            model_item.setData(product_type_icon, PRODUCT_TYPE_ICON_ROLE)
            model_item.setData(product_item.folder_id, FOLDER_ID_ROLE)
            model_item.setData(product_item.folder_label, FOLDER_LABEL_ROLE)

            self._product_items_by_id[product_id] = product_item
            self._items_by_id[product_id] = model_item
        self._set_version_data_to_product_item(model_item, last_version)
        return model_item

    def refresh(self, project_name, folder_ids):
        self._clear()
        product_items = self._controller.get_product_items(
            project_name,
            folder_ids,
            sender=PRODUCTS_MODEL_SENDER_NAME
        )
        product_items_by_id = {
            product_item.product_id: product_item
            for product_item in product_items
        }

        # Prepare product groups
        product_name_matches_by_group = collections.defaultdict(dict)
        for product_item in product_items_by_id.values():
            group_name = None
            if self._grouping_enabled:
                group_name = product_item.group_name

            product_name = product_item.product_name
            group = product_name_matches_by_group[group_name]
            if product_name not in group:
                group[product_name] = [product_item]
                continue
            group[product_name].append(product_item)

        group_names = set(product_name_matches_by_group.keys())

        root_item = self.invisibleRootItem()
        new_root_items = []
        merged_paths = set()
        for group_name in group_names:
            key_parts = []
            if group_name:
                key_parts.append(group_name)

            groups = product_name_matches_by_group[group_name]
            merged_product_items = {}
            top_items = []
            for product_name, product_items in groups.items():
                if len(product_items) == 1:
                    top_items.append(product_items[0])
                else:
                    path = "/".join(key_parts + [product_name])
                    merged_paths.add(path)
                    merged_product_items[path] = product_items

            parent_item = None
            if group_name:
                parent_item = self._get_group_model_item(group_name)

            new_items = []
            if parent_item is not None and parent_item.row() < 0:
                new_root_items.append(parent_item)

            for product_item in top_items:
                item = self._get_product_model_item(product_item)
                new_items.append(item)

            for path, product_items in merged_product_items.items():
                merged_item = self._get_merged_model_item(path)
                new_items.append(merged_item)

                new_merged_items = []
                for product_item in product_items:
                    item = self._get_product_model_item(product_item)
                    new_merged_items.append(item)

                if new_merged_items:
                    merged_item.appendRows(new_merged_items)

            if not new_items:
                continue

            if parent_item is None:
                new_root_items.extend(new_items)
            else:
                parent_item.appendRows(new_items)

        root_item.appendRows(new_root_items)
    # ---------------------------------
    #   This implementation does not call '_clear' at the start
    #       but is more complex and probably slower
    # ---------------------------------
    # def _remove_items(self, items):
    #     if not items:
    #         return
    #     root_item = self.invisibleRootItem()
    #     for item in items:
    #         row = item.row()
    #         if row < 0:
    #             continue
    #         parent = item.parent()
    #         if parent is None:
    #             parent = root_item
    #         parent.removeRow(row)
    #
    # def _remove_group_items(self, group_names):
    #     group_items = [
    #         self._group_items_by_name.pop(group_name)
    #         for group_name in group_names
    #     ]
    #     self._remove_items(group_items)
    #
    # def _remove_merged_items(self, paths):
    #     merged_items = [
    #         self._merged_items_by_id.pop(path)
    #         for path in paths
    #     ]
    #     self._remove_items(merged_items)
    #
    # def _remove_product_items(self, product_ids):
    #     product_items = []
    #     for product_id in product_ids:
    #         self._product_items_by_id.pop(product_id)
    #         product_items.append(self._items_by_id.pop(product_id))
    #     self._remove_items(product_items)
    #
    # def _add_to_new_items(self, item, parent_item, new_items, root_item):
    #     if item.row() < 0:
    #         new_items.append(item)
    #     else:
    #         item_parent = item.parent()
    #         if item_parent is not parent_item:
    #             if item_parent is None:
    #                 item_parent = root_item
    #             item_parent.takeRow(item.row())
    #             new_items.append(item)

    # def refresh(self, project_name, folder_ids):
    #     product_items = self._controller.get_product_items(
    #         project_name,
    #         folder_ids,
    #         sender=PRODUCTS_MODEL_SENDER_NAME
    #     )
    #     product_items_by_id = {
    #         product_item.product_id: product_item
    #         for product_item in product_items
    #     }
    #     # Remove product items that are not available
    #     product_ids_to_remove = (
    #         set(self._items_by_id.keys()) - set(product_items_by_id.keys())
    #     )
    #     self._remove_product_items(product_ids_to_remove)
    #
    #     # Prepare product groups
    #     product_name_matches_by_group = collections.defaultdict(dict)
    #     for product_item in product_items_by_id.values():
    #         group_name = None
    #         if self._grouping_enabled:
    #             group_name = product_item.group_name
    #
    #         product_name = product_item.product_name
    #         group = product_name_matches_by_group[group_name]
    #         if product_name not in group:
    #             group[product_name] = [product_item]
    #             continue
    #         group[product_name].append(product_item)
    #
    #     group_names = set(product_name_matches_by_group.keys())
    #
    #     root_item = self.invisibleRootItem()
    #     new_root_items = []
    #     merged_paths = set()
    #     for group_name in group_names:
    #         key_parts = []
    #         if group_name:
    #             key_parts.append(group_name)
    #
    #         groups = product_name_matches_by_group[group_name]
    #         merged_product_items = {}
    #         top_items = []
    #         for product_name, product_items in groups.items():
    #             if len(product_items) == 1:
    #                 top_items.append(product_items[0])
    #             else:
    #                 path = "/".join(key_parts + [product_name])
    #                 merged_paths.add(path)
    #                 merged_product_items[path] = product_items
    #
    #         parent_item = None
    #         if group_name:
    #             parent_item = self._get_group_model_item(group_name)
    #
    #         new_items = []
    #         if parent_item is not None and parent_item.row() < 0:
    #             new_root_items.append(parent_item)
    #
    #         for product_item in top_items:
    #             item = self._get_product_model_item(product_item)
    #             self._add_to_new_items(
    #                 item, parent_item, new_items, root_item
    #             )
    #
    #         for path, product_items in merged_product_items.items():
    #             merged_item = self._get_merged_model_item(path)
    #             self._add_to_new_items(
    #                 merged_item, parent_item, new_items, root_item
    #             )
    #
    #             new_merged_items = []
    #             for product_item in product_items:
    #                 item = self._get_product_model_item(product_item)
    #                 self._add_to_new_items(
    #                     item, merged_item, new_merged_items, root_item
    #                 )
    #
    #             if new_merged_items:
    #                 merged_item.appendRows(new_merged_items)
    #
    #         if not new_items:
    #             continue
    #
    #         if parent_item is not None:
    #             parent_item.appendRows(new_items)
    #             continue
    #
    #         new_root_items.extend(new_items)
    #
    #     root_item.appendRows(new_root_items)
    #
    #     merged_item_ids_to_remove = (
    #         set(self._merged_items_by_id.keys()) - merged_paths
    #     )
    #     group_names_to_remove = (
    #         set(self._group_items_by_name.keys()) - set(group_names)
    #     )
    #     self._remove_merged_items(merged_item_ids_to_remove)
    #     self._remove_group_items(group_names_to_remove)
