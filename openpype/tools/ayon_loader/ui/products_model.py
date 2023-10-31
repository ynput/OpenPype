import collections

import qtawesome
from qtpy import QtGui, QtCore

from openpype.style import get_default_entity_icon_color
from openpype.tools.ayon_utils.widgets import get_qt_icon

PRODUCTS_MODEL_SENDER_NAME = "qt_products_model"

GROUP_TYPE_ROLE = QtCore.Qt.UserRole + 1
MERGED_COLOR_ROLE = QtCore.Qt.UserRole + 2
FOLDER_LABEL_ROLE = QtCore.Qt.UserRole + 3
FOLDER_ID_ROLE = QtCore.Qt.UserRole + 4
PRODUCT_ID_ROLE = QtCore.Qt.UserRole + 5
PRODUCT_NAME_ROLE = QtCore.Qt.UserRole + 6
PRODUCT_TYPE_ROLE = QtCore.Qt.UserRole + 7
PRODUCT_TYPE_ICON_ROLE = QtCore.Qt.UserRole + 8
PRODUCT_IN_SCENE_ROLE = QtCore.Qt.UserRole + 9
VERSION_ID_ROLE = QtCore.Qt.UserRole + 10
VERSION_HERO_ROLE = QtCore.Qt.UserRole + 11
VERSION_NAME_ROLE = QtCore.Qt.UserRole + 12
VERSION_NAME_EDIT_ROLE = QtCore.Qt.UserRole + 13
VERSION_PUBLISH_TIME_ROLE = QtCore.Qt.UserRole + 14
VERSION_AUTHOR_ROLE = QtCore.Qt.UserRole + 15
VERSION_FRAME_RANGE_ROLE = QtCore.Qt.UserRole + 16
VERSION_DURATION_ROLE = QtCore.Qt.UserRole + 17
VERSION_HANDLES_ROLE = QtCore.Qt.UserRole + 18
VERSION_STEP_ROLE = QtCore.Qt.UserRole + 19
VERSION_AVAILABLE_ROLE = QtCore.Qt.UserRole + 20
VERSION_THUMBNAIL_ID_ROLE = QtCore.Qt.UserRole + 21


class ProductsModel(QtGui.QStandardItemModel):
    refreshed = QtCore.Signal()
    version_changed = QtCore.Signal()
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
    merged_items_colors = [
        ("#{0:02x}{1:02x}{2:02x}".format(*c), QtGui.QColor(*c))
        for c in [
            (55, 161, 222),   # Light Blue
            (231, 176, 0),    # Yellow
            (154, 13, 255),   # Purple
            (130, 184, 30),   # Light Green
            (211, 79, 63),    # Light Red
            (179, 181, 182),  # Grey
            (194, 57, 179),   # Pink
            (0, 120, 215),    # Dark Blue
            (0, 204, 106),    # Dark Green
            (247, 99, 12),    # Orange
        ]
    ]

    version_col = column_labels.index("Version")
    published_time_col = column_labels.index("Time")
    folders_label_col = column_labels.index("Folder")
    in_scene_col = column_labels.index("In scene")

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
        self._grouping_enabled = True
        self._reset_merge_color = False
        self._color_iterator = self._color_iter()
        self._group_icon = None

        self._last_project_name = None
        self._last_folder_ids = []

    def get_product_item_indexes(self):
        return [
            item.index()
            for item in self._items_by_id.values()
        ]

    def get_product_item_by_id(self, product_id):
        """

        Args:
            product_id (str): Product id.

        Returns:
            Union[ProductItem, None]: Product item with version information.
        """

        return self._product_items_by_id.get(product_id)

    def set_enable_grouping(self, enable_grouping):
        if enable_grouping is self._grouping_enabled:
            return
        self._grouping_enabled = enable_grouping
        # Ignore change if groups are not available
        self.refresh(self._last_project_name, self._last_folder_ids)

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
            return list(product_item.version_items.values())

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
                role = PRODUCT_IN_SCENE_ROLE
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
            final_version_item = None
            for v_id, version_item in product_item.version_items.items():
                if v_id == value:
                    final_version_item = version_item
                    break

            if final_version_item is None:
                return False
            if index.data(VERSION_ID_ROLE) == final_version_item.version_id:
                return True
            item = self.itemFromIndex(index)
            self._set_version_data_to_product_item(item, final_version_item)
            self.version_changed.emit()
            return True
        return super(ProductsModel, self).setData(index, value, role)

    def _get_next_color(self):
        return next(self._color_iterator)

    def _color_iter(self):
        while True:
            for color in self.merged_items_colors:
                if self._reset_merge_color:
                    self._reset_merge_color = False
                    break
                yield color

    def _clear(self):
        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())

        self._items_by_id = {}
        self._group_items_by_name = {}
        self._merged_items_by_id = {}
        self._product_items_by_id = {}
        self._reset_merge_color = True

    def _get_group_icon(self):
        if self._group_icon is None:
            self._group_icon = qtawesome.icon(
                "fa.object-group",
                color=get_default_entity_icon_color()
            )
        return self._group_icon

    def _get_group_model_item(self, group_name):
        model_item = self._group_items_by_name.get(group_name)
        if model_item is None:
            model_item = QtGui.QStandardItem(group_name)
            model_item.setData(
                self._get_group_icon(), QtCore.Qt.DecorationRole
            )
            model_item.setData(0, GROUP_TYPE_ROLE)
            model_item.setEditable(False)
            model_item.setColumnCount(self.columnCount())
            self._group_items_by_name[group_name] = model_item
        return model_item

    def _get_merged_model_item(self, path, count, hex_color):
        model_item = self._merged_items_by_id.get(path)
        if model_item is None:
            model_item = QtGui.QStandardItem()
            model_item.setData(1, GROUP_TYPE_ROLE)
            model_item.setData(hex_color, MERGED_COLOR_ROLE)
            model_item.setEditable(False)
            model_item.setColumnCount(self.columnCount())
            self._merged_items_by_id[path] = model_item
        label = "{} ({})".format(path, count)
        model_item.setData(label, QtCore.Qt.DisplayRole)
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
        model_item.setData(
            version_item.thumbnail_id, VERSION_THUMBNAIL_ID_ROLE)

    def _get_product_model_item(self, product_item):
        model_item = self._items_by_id.get(product_item.product_id)
        versions = list(product_item.version_items.values())
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

            self._product_items_by_id[product_id] = product_item
            self._items_by_id[product_id] = model_item

        model_item.setData(product_item.folder_label, FOLDER_LABEL_ROLE)
        in_scene = 1 if product_item.product_in_scene else 0
        model_item.setData(in_scene, PRODUCT_IN_SCENE_ROLE)

        self._set_version_data_to_product_item(model_item, last_version)
        return model_item

    def get_last_project_name(self):
        return self._last_project_name

    def refresh(self, project_name, folder_ids):
        self._clear()

        self._last_project_name = project_name
        self._last_folder_ids = folder_ids

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
            group_product_types = set()
            for product_name, product_items in groups.items():
                group_product_types |= {p.product_type for p in product_items}
                if len(product_items) == 1:
                    top_items.append(product_items[0])
                else:
                    path = "/".join(key_parts + [product_name])
                    merged_paths.add(path)
                    merged_product_items[path] = (
                        product_name,
                        product_items,
                    )

            parent_item = None
            if group_name:
                parent_item = self._get_group_model_item(group_name)
                parent_item.setData(
                    "|".join(group_product_types), PRODUCT_TYPE_ROLE)

            new_items = []
            if parent_item is not None and parent_item.row() < 0:
                new_root_items.append(parent_item)

            for product_item in top_items:
                item = self._get_product_model_item(product_item)
                new_items.append(item)

            for path_info in merged_product_items.values():
                product_name, product_items = path_info
                (merged_color_hex, merged_color_qt) = self._get_next_color()
                merged_color = qtawesome.icon(
                    "fa.circle", color=merged_color_qt)
                merged_item = self._get_merged_model_item(
                    product_name, len(product_items), merged_color_hex)
                merged_item.setData(merged_color, QtCore.Qt.DecorationRole)
                new_items.append(merged_item)

                merged_product_types = set()
                new_merged_items = []
                for product_item in product_items:
                    item = self._get_product_model_item(product_item)
                    new_merged_items.append(item)
                    merged_product_types.add(product_item.product_type)

                merged_item.setData(
                    "|".join(merged_product_types), PRODUCT_TYPE_ROLE)
                if new_merged_items:
                    merged_item.appendRows(new_merged_items)

            if not new_items:
                continue

            if parent_item is None:
                new_root_items.extend(new_items)
            else:
                parent_item.appendRows(new_items)

        if new_root_items:
            root_item.appendRows(new_root_items)

        self.refreshed.emit()
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
