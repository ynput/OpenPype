from qtpy import QtWidgets

from openpype.tools.utils.delegates import PrettyTimeDelegate
from openpype.tools.utils import (
    RecursiveSortFilterProxyModel,
    DeselectableTreeView,
)

from .products_model import ProductsModel, PRODUCTS_MODEL_SENDER_NAME
from .products_delegates import VersionDelegate


class ProductsWidget(QtWidgets.QWidget):
    default_widths = (
        200, # Product name
        90,  # Product type
        130, # Folder label
        60,  # Version
        125, # Time
        75,  # Author
        75,  # Frames
        60,  # Duration
        55,  # Handles
        10,  # Step
        25,  # Loaded in scene
        65,  # Site info (maybe?)
    )

    def __init__(self, controller, parent):
        super(ProductsWidget, self).__init__(parent)

        self._controller = controller

        products_view = DeselectableTreeView(self)
        products_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        products_model = ProductsModel(controller)
        products_proxy_model = RecursiveSortFilterProxyModel()
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

    def set_name_filer(self, name):
        """Set filter of product name.

        Args:
            name (str): The string filter.
        """

        self._products_proxy_model.setFilterFixedString(name)

    def _refresh_model(self):
        self._products_model.refresh(
            self._selected_project_name,
            self._selected_folder_ids
        )

    def _on_folders_selection_change(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_ids = event["folder_ids"]
        self._refresh_model()

    def _on_products_refresh_finished(self, event):
        if event["sender"] != PRODUCTS_MODEL_SENDER_NAME:
            self._refresh_model()
