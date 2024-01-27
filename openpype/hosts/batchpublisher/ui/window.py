from openpype import style

from qtpy import QtWidgets

from openpype.hosts.batchpublisher import controller
from .batch_publisher_model import BatchPublisherModel
from .batch_publisher_delegate import BatchPublisherTableDelegate
from .batch_publisher_view import BatchPublisherTableView


class BatchPublisherWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(BatchPublisherWindow, self).__init__(parent)

        self.setWindowTitle("AYON Batch Publisher")
        self.resize(1750, 900)

        main_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(main_widget)

        # --- Top inputs (project, directory) ---
        top_inputs_widget = QtWidgets.QWidget(self)

        self._project_combobox = QtWidgets.QComboBox(top_inputs_widget)
        self._project_combobox.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed)

        dir_inputs_widget = QtWidgets.QWidget(top_inputs_widget)
        dir_input = QtWidgets.QLineEdit(dir_inputs_widget)
        dir_browse_btn = QtWidgets.QPushButton("Browse", dir_inputs_widget)

        dir_inputs_layout = QtWidgets.QHBoxLayout(dir_inputs_widget)
        dir_inputs_layout.setContentsMargins(0, 0, 0, 0)
        dir_inputs_layout.addWidget(dir_input, 1)
        dir_inputs_layout.addWidget(dir_browse_btn, 0)

        top_inputs_layout = QtWidgets.QFormLayout(top_inputs_widget)
        top_inputs_layout.setContentsMargins(0, 0, 0, 0)
        top_inputs_layout.addRow("Choose project", self._project_combobox)
        # pushbutton_change_project = QtWidgets.QPushButton("Change project")
        # top_inputs_layout.addRow(pushbutton_change_project)
        top_inputs_layout.addRow("Directory to ingest", dir_inputs_widget)

        self._controller = controller.BatchPublisherController()

        # --- Main view ---
        table_view = BatchPublisherTableView(self._controller, main_widget)

        # --- Footer ---
        footer_widget = QtWidgets.QWidget(main_widget)

        publish_btn = QtWidgets.QPushButton("Publish", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(publish_btn, 0)

        # --- Main layout ---
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        main_layout.addWidget(top_inputs_widget, 0)
        main_layout.addWidget(table_view, 1)
        main_layout.addWidget(footer_widget, 0)

        self.setStyleSheet(style.load_stylesheet())

        self._project_combobox.currentIndexChanged.connect(
            self._on_project_changed)
        # pushbutton_change_project.clicked.connect(self._on_project_changed)
        dir_browse_btn.clicked.connect(self._on_browse_button_clicked)
        publish_btn.clicked.connect(self._on_publish_button_clicked)

        editors_delegate = BatchPublisherTableDelegate(self._controller)
        table_view.setItemDelegateForColumn(
            BatchPublisherModel.COLUMN_OF_FOLDER,
            editors_delegate)
        table_view.setItemDelegateForColumn(
            BatchPublisherModel.COLUMN_OF_TASK,
            editors_delegate)
        table_view.setItemDelegateForColumn(
            BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE,
            editors_delegate)
        dir_input.textChanged.connect(self._on_dir_change)

        # self._project_combobox = project_combobox
        self._dir_input = dir_input
        self._table_view = table_view
        self._editors_delegate = editors_delegate
        self._pushbutton_publish = publish_btn

        self._first_show = True

    def showEvent(self, event):
        super(BatchPublisherWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()

    def _on_first_show(self):
        project_names = sorted(self._controller.get_project_names())
        for project_name in project_names:
            self._project_combobox.addItem(project_name)

    def _on_project_changed(self):
        project_name = str(self._project_combobox.currentText())
        self._controller.set_selected_project_name(project_name)
        self._table_view._model._change_project(project_name)

    def _on_browse_button_clicked(self):
        directory = self._dir_input.text()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            dir=directory)
        if not directory:
            return
        self._dir_input.setText(directory)

    def _on_dir_change(self, directory):
        self._table_view.set_current_directory(directory)

    def _on_publish_button_clicked(self):
        product_item = self._table_view.get_product_items()
        publish_count = 0
        enabled_count = 0
        defined_count = 0
        for product_item in product_item:
            if product_item.enabled and product_item.defined:
                publish_count += 1
            if product_item.enabled:
                enabled_count += 1
            if product_item.defined:
                defined_count += 1

        if publish_count == 0:
            msg = "You must provide asset, task, family, "
            msg += "subset etc and they must be enabled"
            QtWidgets.QMessageBox.warning(
                None,
                "No enabled and defined ingest items!",
                msg)
            return
        elif publish_count > 0:
            msg = "Are you sure you want to publish "
            msg += "{} products".format(publish_count)
            result = QtWidgets.QMessageBox.question(
                None,
                "Okay to publish?",
                msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if result == QtWidgets.QMessageBox.No:
                print("User cancelled publishing")
                return
        elif enabled_count == 0:
            QtWidgets.QMessageBox.warning(
                None,
                "Nothing enabled for publish!",
                "There is no items enabled for publish")
            return
        elif defined_count == 0:
            QtWidgets.QMessageBox.warning(
                None,
                "No defined ingest items!",
                "You must provide asset, task, family, subset etc")
            return

        self._controller.publish_product_item(product_item)


def main():
    batch_publisher = BatchPublisherWindow()
    batch_publisher.show()
