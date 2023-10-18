from qtpy import QtWidgets

from openpype.tools.utils import PlaceholderLineEdit


class ProductGroupDialog(QtWidgets.QDialog):
    def __init__(self, controller, parent):
        super(ProductGroupDialog, self).__init__(parent)
        self.setWindowTitle("Grouping products")
        self.setMinimumWidth(250)
        self.setModal(True)

        main_label = QtWidgets.QLabel("Group Name", self)

        group_name_input = PlaceholderLineEdit(self)
        group_name_input.setPlaceholderText("Remain blank to ungroup..")

        group_btn = QtWidgets.QPushButton("Apply", self)
        group_btn.setAutoDefault(True)
        group_btn.setDefault(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(main_label, 0)
        layout.addWidget(group_name_input, 0)
        layout.addWidget(group_btn, 0)

        group_btn.clicked.connect(self._on_apply_click)

        self._project_name = None
        self._product_ids = set()

        self._controller = controller
        self._group_btn = group_btn
        self._group_name_input = group_name_input

    def set_product_ids(self, project_name, product_ids):
        self._project_name = project_name
        self._product_ids = product_ids

    def _on_apply_click(self):
        group_name = self._group_name_input.text().strip() or None
        self._controller.change_products_group(
            self._project_name, self._product_ids, group_name
        )
        self.close()
