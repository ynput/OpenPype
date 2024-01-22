

from openpype import style

from openpype.client.entities import get_projects

from qtpy import QtWidgets

from openpype.hosts.batchpublisher import controller
from openpype.hosts.batchpublisher.models import batch_publisher_model
from openpype.hosts.batchpublisher.delegates import batch_publisher_delegate
from openpype.hosts.batchpublisher.views import batch_publisher_view


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
        table_view = batch_publisher_view.BatchPublisherTableView(
            self._controller,
            main_widget)

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

        # TODO do not use query in __init__
        # - add QStandardItemModel that handles refresh, or implement refresh
        #   on the window
        projects = get_projects()
        for project_dict in projects:
            self._project_combobox.addItem(project_dict["name"])

        editors_delegate = batch_publisher_delegate. \
            BatchPublisherTableDelegate(self._controller)
        table_view.setItemDelegateForColumn(
            batch_publisher_model.BatchPublisherModel.COLUMN_OF_FOLDER,
            editors_delegate)
        table_view.setItemDelegateForColumn(
            batch_publisher_model.BatchPublisherModel.COLUMN_OF_TASK,
            editors_delegate)
        table_view.setItemDelegateForColumn(
            batch_publisher_model.BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE,
            editors_delegate)

        # self._project_combobox = project_combobox
        self._dir_input = dir_input
        self._table_view = table_view
        self._editors_delegate = editors_delegate
        self._pushbutton_publish = publish_btn

    def _on_project_changed(self):
        project_name = str(self._project_combobox.currentText())
        self._controller.project_name = project_name

    def _on_browse_button_clicked(self):
        directory = self._dir_input.text()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            dir=directory)
        if not directory:
            return
        self._dir_input.setText(directory)
        self._controller.populate_from_directory(directory)

    def _on_publish_button_clicked(self):
        self._table_view.publish()


def main():
    batch_publisher = BatchPublisherWindow()
    batch_publisher.show()
