from qtpy import QtWidgets, QtCore

from openpype.tools.utils.delegates import PrettyTimeDelegate
from openpype.tools.utils import (
    RecursiveSortFilterProxyModel,
    DeselectableTreeView,
)

from .products_model import (
    ProductsModel,
    PRODUCTS_MODEL_SENDER_NAME,
    PRODUCT_TYPE_ROLE,
    GROUP_TYPE_ROLE,
)
from .products_delegates import VersionDelegate


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

        # version_delegate = VersionDelegate()
        # products_view.setItemDelegateForColumn(
        #     products_model.version_col, version_delegate)

        time_delegate = PrettyTimeDelegate()
        products_view.setItemDelegateForColumn(
            products_model.published_time_col, time_delegate)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(products_view, 1)

        controller.register_event_callback(
            "selection.folders.changed",
            self._on_folders_selection_change,
        )
        controller.register_event_callback(
            "products.refresh.finished",
            self._on_products_refresh_finished
        )
        # controller.register_event_callback(
        #     "controller.refresh.finished",
        #     self._on_controller_refresh
        # )
        # controller.register_event_callback(
        #     "expected_selection_changed",
        #     self._on_expected_selection_change
        # )

        self._products_view = products_view
        self._products_model = products_model
        self._products_proxy_model = products_proxy_model

        self._selected_project_name = None
        self._selected_folder_ids = set()

        # Set initial state of widget
        self._update_folders_label_visible()

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

    def _refresh_model(self):
        self._products_model.refresh(
            self._selected_project_name,
            self._selected_folder_ids
        )

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
