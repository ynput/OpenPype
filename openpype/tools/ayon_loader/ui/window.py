from qtpy import QtWidgets, QtCore, QtGui

from openpype.resources import get_openpype_icon_filepath
from openpype.style import load_stylesheet
from openpype.tools.utils import PlaceholderLineEdit
from openpype.tools.ayon_utils.widgets import ProjectsCombobox
from openpype.tools.ayon_loader.control import LoaderController

from .folders_widget import LoaderFoldersWidget
from .products_widget import ProductsWidget
from .product_types_widget import ProductTypesView


class LoaderWindow(QtWidgets.QWidget):
    def __init__(self, controller=None, parent=None):
        super(LoaderWindow, self).__init__(parent)

        icon = QtGui.QIcon(get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Loader")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        if controller is None:
            controller = LoaderController()

        main_splitter = QtWidgets.QSplitter(self)

        context_splitter = QtWidgets.QSplitter(main_splitter)
        context_splitter.setOrientation(QtCore.Qt.Vertical)

        # Context selection widget
        context_widget = QtWidgets.QWidget(context_splitter)

        projects_combobox = ProjectsCombobox(controller, context_widget)
        projects_combobox.set_select_item_visible(True)

        folders_filter_input = PlaceholderLineEdit(context_widget)
        folders_filter_input.setPlaceholderText("Folder name filter...")

        folders_widget = LoaderFoldersWidget(controller, context_widget)

        product_types_widget = ProductTypesView(controller, context_splitter)

        context_layout = QtWidgets.QVBoxLayout(context_widget)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.addWidget(projects_combobox, 0)
        context_layout.addWidget(folders_filter_input, 0)
        context_layout.addWidget(folders_widget, 1)

        context_splitter.addWidget(context_widget)
        context_splitter.addWidget(product_types_widget)
        context_splitter.setStretchFactor(0, 65)
        context_splitter.setStretchFactor(1, 35)

        # Subset + version selection item
        products_wrap_widget = QtWidgets.QWidget(main_splitter)

        products_inputs_widget = QtWidgets.QWidget(products_wrap_widget)

        products_filter_input = PlaceholderLineEdit(products_inputs_widget)
        products_filter_input.setPlaceholderText("Product name filter...")
        product_group_checkbox = QtWidgets.QCheckBox(
            "Enable grouping", products_inputs_widget)
        product_group_checkbox.setChecked(True)

        products_widget = ProductsWidget(controller, products_wrap_widget)

        products_inputs_layout = QtWidgets.QHBoxLayout(products_inputs_widget)
        products_inputs_layout.setContentsMargins(0, 0, 0, 0)
        products_inputs_layout.addWidget(products_filter_input, 1)
        products_inputs_layout.addWidget(product_group_checkbox, 0)

        products_wrap_layout = QtWidgets.QVBoxLayout(products_wrap_widget)
        products_wrap_layout.setContentsMargins(0, 0, 0, 0)
        products_wrap_layout.addWidget(products_inputs_widget, 0)
        products_wrap_layout.addWidget(products_widget, 1)

        main_splitter.addWidget(context_splitter)
        main_splitter.addWidget(products_wrap_widget)

        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 7)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(main_splitter)

        show_timer = QtCore.QTimer()
        show_timer.setInterval(1)

        show_timer.timeout.connect(self._on_show_timer)

        folders_filter_input.textChanged.connect(
            self._on_folder_filete_change
        )
        product_types_widget.filter_changed.connect(
            self._on_product_type_filter_change
        )
        product_group_checkbox.stateChanged.connect(
            self._on_product_group_change)

        self._projects_combobox = projects_combobox

        self._folders_filter_input = folders_filter_input
        self._folders_widget = folders_widget

        self._product_types_widget = product_types_widget

        self._products_filter_input = products_filter_input
        self._product_group_checkbox = product_group_checkbox
        self._products_widget = products_widget

        self._controller = controller
        self._first_show = True
        self._reset_on_show = True
        self._show_counter = 0
        self._show_timer = show_timer

    def showEvent(self, event):
        super(LoaderWindow, self).showEvent(event)

        if self._first_show:
            self._on_first_show()

        self._show_timer.start()

    def _on_first_show(self):
        self._first_show = False
        # if self._controller.is_site_sync_enabled():
        #     self.resize(1800, 900)
        # else:
        #     self.resize(1300, 700)
        self.resize(1300, 700)
        self.setStyleSheet(load_stylesheet())
        self._controller.reset()

    def _on_show_timer(self):
        if self._show_counter < 2:
            self._show_counter += 1
            return

        self._show_counter = 0
        self._show_timer.stop()

        if self._reset_on_show:
            self._reset_on_show = False
            self._controller.reset()

    def _on_folder_filete_change(self, text):
        self._folders_widget.set_name_filer(text)

    def _on_product_group_change(self):
        self._products_widget.set_enable_grouping(
            self._product_group_checkbox.isChecked()
        )

    def _on_product_type_filter_change(self):
        self._products_widget.set_product_type_filter(
            self._product_types_widget.get_filter_info()
        )
