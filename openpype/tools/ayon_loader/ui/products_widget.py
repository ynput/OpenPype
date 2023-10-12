import collections

from qtpy import QtWidgets, QtCore

from openpype.tools.utils import (
    RecursiveSortFilterProxyModel,
    DeselectableTreeView,
)
from openpype.tools.utils.delegates import PrettyTimeDelegate

from .products_model import (
    ProductsModel,
    PRODUCTS_MODEL_SENDER_NAME,
    PRODUCT_TYPE_ROLE,
    GROUP_TYPE_ROLE,
    MERGED_COLOR_ROLE,
    FOLDER_ID_ROLE,
    PRODUCT_ID_ROLE,
    VERSION_ID_ROLE,
    VERSION_THUMBNAIL_ID_ROLE,
)
from .products_delegates import VersionDelegate, LoadedInSceneDelegate
from .actions_utils import show_actions_menu


class ProductsProxyModel(RecursiveSortFilterProxyModel):
    def __init__(self, parent=None):
        super(ProductsProxyModel, self).__init__(parent)

        self._product_type_filters = {}
        self._ascending_sort = True

    def set_product_type_filters(self, product_type_filters):
        self._product_type_filters = product_type_filters
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        source_model = self.sourceModel()
        index = source_model.index(source_row, 0, source_parent)
        product_types_s = source_model.data(index, PRODUCT_TYPE_ROLE)
        product_types = []
        if product_types_s:
            product_types = product_types_s.split("|")

        for product_type in product_types:
            if not self._product_type_filters.get(product_type, True):
                return False
        return super(ProductsProxyModel, self).filterAcceptsRow(
            source_row, source_parent)

    def lessThan(self, left, right):
        l_model = left.model()
        r_model = right.model()
        left_group_type = l_model.data(left, GROUP_TYPE_ROLE)
        right_group_type = r_model.data(right, GROUP_TYPE_ROLE)
        # Groups are always on top, merged product types are below
        #   and items without group at the bottom
        # QUESTION Do we need to do it this way?
        if left_group_type != right_group_type:
            if left_group_type is None:
                output = False
            elif right_group_type is None:
                output = True
            else:
                output = left_group_type < right_group_type
            if not self._ascending_sort:
                output = not output
            return output
        return super(ProductsProxyModel, self).lessThan(left, right)

    def sort(self, column, order=None):
        if order is None:
            order = QtCore.Qt.AscendingOrder
        self._ascending_sort = order == QtCore.Qt.AscendingOrder
        super(ProductsProxyModel, self).sort(column, order)


class ProductsWidget(QtWidgets.QWidget):
    refreshed = QtCore.Signal()
    merged_products_selection_changed = QtCore.Signal()
    selection_changed = QtCore.Signal()
    version_changed = QtCore.Signal()
    default_widths = (
        200,  # Product name
        90,   # Product type
        130,  # Folder label
        60,   # Version
        125,  # Time
        75,   # Author
        75,   # Frames
        60,   # Duration
        55,   # Handles
        10,   # Step
        25,   # Loaded in scene
        65,   # Site info (maybe?)
    )

    def __init__(self, controller, parent):
        super(ProductsWidget, self).__init__(parent)

        self._controller = controller

        products_view = DeselectableTreeView(self)
        # TODO - define custom object name in style
        products_view.setObjectName("SubsetView")
        products_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        products_view.setAllColumnsShowFocus(True)
        # TODO - add context menu
        products_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        products_view.setSortingEnabled(True)
        # Sort by product type
        products_view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        products_view.setAlternatingRowColors(True)

        products_model = ProductsModel(controller)
        products_proxy_model = ProductsProxyModel()
        products_proxy_model.setSourceModel(products_model)

        products_view.setModel(products_proxy_model)

        for idx, width in enumerate(self.default_widths):
            products_view.setColumnWidth(idx, width)

        version_delegate = VersionDelegate()
        products_view.setItemDelegateForColumn(
            products_model.version_col, version_delegate)

        time_delegate = PrettyTimeDelegate()
        products_view.setItemDelegateForColumn(
            products_model.published_time_col, time_delegate)

        in_scene_delegate = LoadedInSceneDelegate()
        products_view.setItemDelegateForColumn(
            products_model.in_scene_col, in_scene_delegate)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(products_view, 1)

        products_proxy_model.rowsInserted.connect(self._on_rows_inserted)
        products_proxy_model.rowsMoved.connect(self._on_rows_moved)
        products_model.refreshed.connect(self._on_refresh)
        products_view.customContextMenuRequested.connect(
            self._on_context_menu)
        products_view.selectionModel().selectionChanged.connect(
            self._on_selection_change)
        products_model.version_changed.connect(self._on_version_change)

        controller.register_event_callback(
            "selection.folders.changed",
            self._on_folders_selection_change,
        )
        controller.register_event_callback(
            "products.refresh.finished",
            self._on_products_refresh_finished
        )
        controller.register_event_callback(
            "products.group.changed",
            self._on_group_changed
        )

        self._products_view = products_view
        self._products_model = products_model
        self._products_proxy_model = products_proxy_model

        self._version_delegate = version_delegate
        self._time_delegate = time_delegate

        self._selected_project_name = None
        self._selected_folder_ids = set()

        self._selected_merged_products = []
        self._selected_versions_info = []

        # Set initial state of widget
        # - Hide folders column
        self._update_folders_label_visible()
        # - Hide in scene column if is not supported (this won't change)
        products_view.setColumnHidden(
            products_model.in_scene_col,
            not controller.is_loaded_products_supported()
        )

    def set_name_filer(self, name):
        """Set filter of product name.

        Args:
            name (str): The string filter.
        """

        self._products_proxy_model.setFilterFixedString(name)

    def set_product_type_filter(self, product_type_filters):
        """

        Args:
            product_type_filters (dict[str, bool]): The filter of product
                types.
        """

        self._products_proxy_model.set_product_type_filters(
            product_type_filters
        )

    def set_enable_grouping(self, enable_grouping):
        self._products_model.set_enable_grouping(enable_grouping)

    def get_selected_merged_products(self):
        return self._selected_merged_products

    def get_selected_version_info(self):
        return self._selected_versions_info

    def refresh(self):
        self._refresh_model()

    def _fill_version_editor(self):
        model = self._products_proxy_model
        index_queue = collections.deque()
        for row in range(model.rowCount()):
            index_queue.append((row, None))

        version_col = self._products_model.version_col
        while index_queue:
            (row, parent_index) = index_queue.popleft()
            args = [row, 0]
            if parent_index is not None:
                args.append(parent_index)
            index = model.index(*args)
            rows = model.rowCount(index)
            for row in range(rows):
                index_queue.append((row, index))

            product_id = model.data(index, PRODUCT_ID_ROLE)
            if product_id is not None:
                args[1] = version_col
                v_index = model.index(*args)
                self._products_view.openPersistentEditor(v_index)

    def _on_refresh(self):
        self._fill_version_editor()
        self.refreshed.emit()

    def _on_rows_inserted(self):
        self._fill_version_editor()

    def _on_rows_moved(self):
        self._fill_version_editor()

    def _refresh_model(self):
        self._products_model.refresh(
            self._selected_project_name,
            self._selected_folder_ids
        )

    def _on_context_menu(self, point):
        selection_model = self._products_view.selectionModel()
        model = self._products_view.model()
        project_name = self._products_model.get_last_project_name()

        version_ids = set()
        indexes_queue = collections.deque()
        indexes_queue.extend(selection_model.selectedIndexes())
        while indexes_queue:
            index = indexes_queue.popleft()
            for row in range(model.rowCount(index)):
                child_index = model.index(row, 0, index)
                indexes_queue.append(child_index)
            version_id = model.data(index, VERSION_ID_ROLE)
            if version_id is not None:
                version_ids.add(version_id)

        action_items = self._controller.get_versions_action_items(
            project_name, version_ids)

        # Prepare global point where to show the menu
        global_point = self._products_view.mapToGlobal(point)

        result = show_actions_menu(
            action_items,
            global_point,
            len(version_ids) == 1,
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

    def _on_selection_change(self):
        selected_merged_products = []
        selection_model = self._products_view.selectionModel()
        model = self._products_view.model()
        indexes_queue = collections.deque()
        indexes_queue.extend(selection_model.selectedIndexes())

        # Helper for 'version_items' to avoid duplicated items
        all_product_ids = set()
        selected_version_ids = set()
        # Version items contains information about selected version items
        selected_versions_info = []
        while indexes_queue:
            index = indexes_queue.popleft()
            if index.column() != 0:
                continue

            group_type = model.data(index, GROUP_TYPE_ROLE)
            if group_type is None:
                product_id = model.data(index, PRODUCT_ID_ROLE)
                # Skip duplicates - when group and item are selected the item
                #   would be in the loop multiple times
                if product_id in all_product_ids:
                    continue

                all_product_ids.add(product_id)

                version_id = model.data(index, VERSION_ID_ROLE)
                selected_version_ids.add(version_id)

                thumbnail_id = model.data(index, VERSION_THUMBNAIL_ID_ROLE)
                selected_versions_info.append({
                    "folder_id": model.data(index, FOLDER_ID_ROLE),
                    "product_id": product_id,
                    "version_id": version_id,
                    "thumbnail_id": thumbnail_id,
                })
                continue

            if group_type == 0:
                for row in range(model.rowCount(index)):
                    child_index = model.index(row, 0, index)
                    indexes_queue.append(child_index)
                continue

            if group_type != 1:
                continue

            item_folder_ids = set()
            for row in range(model.rowCount(index)):
                child_index = model.index(row, 0, index)
                indexes_queue.append(child_index)

                folder_id = model.data(child_index, FOLDER_ID_ROLE)
                item_folder_ids.add(folder_id)

            if not item_folder_ids:
                continue

            hex_color = model.data(index, MERGED_COLOR_ROLE)
            item_data = {
                "color": hex_color,
                "folder_ids": item_folder_ids
            }
            selected_merged_products.append(item_data)

        prev_selected_merged_products = self._selected_merged_products
        self._selected_merged_products = selected_merged_products
        self._selected_versions_info = selected_versions_info

        if selected_merged_products != prev_selected_merged_products:
            self.merged_products_selection_changed.emit()
        self.selection_changed.emit()
        self._controller.set_selected_versions(selected_version_ids)

    def _on_version_change(self):
        self._on_selection_change()

    def _on_folders_selection_change(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_ids = event["folder_ids"]
        self._refresh_model()
        self._update_folders_label_visible()

    def _update_folders_label_visible(self):
        folders_label_hidden = len(self._selected_folder_ids) <= 1
        self._products_view.setColumnHidden(
            self._products_model.folders_label_col,
            folders_label_hidden
        )

    def _on_products_refresh_finished(self, event):
        if event["sender"] != PRODUCTS_MODEL_SENDER_NAME:
            self._refresh_model()

    def _on_group_changed(self, event):
        if event["project_name"] != self._selected_project_name:
            return
        folder_ids = event["folder_ids"]
        if not set(folder_ids).intersection(set(self._selected_folder_ids)):
            return
        self.refresh()
