"""Tool for generating asset usage report.

This tool is used to generate asset usage report for a project.
It is using links between published version to find out where
the asset is used.

"""

import csv
import time

import appdirs
import qtawesome
from pymongo.collection import Collection
from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QClipboard, QColor

from openpype import style
from openpype.client import OpenPypeMongoConnection
from openpype.lib import JSONSettingRegistry
from openpype.tools.utils import PlaceholderLineEdit, get_openpype_qt_app
from openpype.tools.utils.constants import PROJECT_NAME_ROLE
from openpype.tools.utils.models import ProjectModel, ProjectSortFilterProxy


class AssetReporterRegistry(JSONSettingRegistry):
    """Class handling OpenPype general settings registry.

    This is used to store last selected project.

    Attributes:
        vendor (str): Name used for path construction.
        product (str): Additional name used for path construction.

    """

    def __init__(self):
        self.vendor = "ynput"
        self.product = "openpype"
        name = "asset_usage_reporter"
        path = appdirs.user_data_dir(self.product, self.vendor)
        super(AssetReporterRegistry, self).__init__(name, path)


class OverlayWidget(QtWidgets.QFrame):
    """Overlay widget for choosing project.

    This code is taken from the Tray Publisher tool.
    """
    project_selected = QtCore.Signal(str)

    def __init__(self, publisher_window):
        super(OverlayWidget, self).__init__(publisher_window)
        self.setObjectName("OverlayFrame")

        middle_frame = QtWidgets.QFrame(self)
        middle_frame.setObjectName("ChooseProjectFrame")

        content_widget = QtWidgets.QWidget(middle_frame)

        header_label = QtWidgets.QLabel("Choose project", content_widget)
        header_label.setObjectName("ChooseProjectLabel")
        # Create project models and view
        projects_model = ProjectModel()
        projects_proxy = ProjectSortFilterProxy()
        projects_proxy.setSourceModel(projects_model)
        projects_proxy.setFilterKeyColumn(0)

        projects_view = QtWidgets.QListView(content_widget)
        projects_view.setObjectName("ChooseProjectView")
        projects_view.setModel(projects_proxy)
        projects_view.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )

        confirm_btn = QtWidgets.QPushButton("Confirm", content_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", content_widget)
        cancel_btn.setVisible(False)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(cancel_btn, 0)
        btns_layout.addWidget(confirm_btn, 0)

        txt_filter = PlaceholderLineEdit(content_widget)
        txt_filter.setPlaceholderText("Quick filter projects..")
        txt_filter.setClearButtonEnabled(True)
        txt_filter.addAction(qtawesome.icon("fa.filter", color="gray"),
                             QtWidgets.QLineEdit.LeadingPosition)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        content_layout.addWidget(header_label, 0)
        content_layout.addWidget(txt_filter, 0)
        content_layout.addWidget(projects_view, 1)
        content_layout.addLayout(btns_layout, 0)

        middle_layout = QtWidgets.QHBoxLayout(middle_frame)
        middle_layout.setContentsMargins(30, 30, 10, 10)
        middle_layout.addWidget(content_widget)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addStretch(1)
        main_layout.addWidget(middle_frame, 2)
        main_layout.addStretch(1)

        projects_view.doubleClicked.connect(self._on_double_click)
        confirm_btn.clicked.connect(self._on_confirm_click)
        cancel_btn.clicked.connect(self._on_cancel_click)
        txt_filter.textChanged.connect(self._on_text_changed)

        self._projects_view = projects_view
        self._projects_model = projects_model
        self._projects_proxy = projects_proxy
        self._cancel_btn = cancel_btn
        self._confirm_btn = confirm_btn
        self._txt_filter = txt_filter

        self._publisher_window = publisher_window
        self._project_name = None

    def showEvent(self, event):
        self._projects_model.refresh()
        # Sort projects after refresh
        self._projects_proxy.sort(0)

        setting_registry = AssetReporterRegistry()
        try:
            project_name = str(setting_registry.get_item("project_name"))
        except ValueError:
            project_name = None

        if project_name:
            index = None
            src_index = self._projects_model.find_project(project_name)
            if src_index is not None:
                index = self._projects_proxy.mapFromSource(src_index)

            if index is not None:
                selection_model = self._projects_view.selectionModel()
                selection_model.select(
                    index,
                    QtCore.QItemSelectionModel.SelectCurrent
                )
                self._projects_view.setCurrentIndex(index)

        self._cancel_btn.setVisible(self._project_name is not None)
        super(OverlayWidget, self).showEvent(event)

    def _on_double_click(self):
        self.set_selected_project()

    def _on_confirm_click(self):
        self.set_selected_project()

    def _on_cancel_click(self):
        self._set_project(self._project_name)

    def _on_text_changed(self):
        self._projects_proxy.setFilterRegularExpression(
            self._txt_filter.text())

    def set_selected_project(self):
        index = self._projects_view.currentIndex()

        if project_name := index.data(PROJECT_NAME_ROLE):
            self._set_project(project_name)

    def _set_project(self, project_name):
        self._project_name = project_name
        self.setVisible(False)
        self.project_selected.emit(project_name)

        setting_registry = AssetReporterRegistry()
        setting_registry.set_item("project_name", project_name)


class AssetReporterWindow(QtWidgets.QDialog):
    default_width = 1000
    default_height = 800
    _content = None

    def __init__(self, parent=None, controller=None, reset_on_show=None):
        super(AssetReporterWindow, self).__init__(parent)

        self._result = {}
        self.setObjectName("AssetReporterWindow")

        self.setWindowTitle("Asset Usage Reporter")

        if parent is None:
            on_top_flag = QtCore.Qt.WindowStaysOnTopHint
        else:
            on_top_flag = QtCore.Qt.Dialog

        self.setWindowFlags(
            QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
            | on_top_flag
        )
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setColumnWidth(0, 400)
        self.table.setColumnWidth(1, 300)
        self.table.setHorizontalHeaderLabels(["Subset", "Used in", "Version"])

        # self.text_area = QtWidgets.QTextEdit(self)
        self.copy_button = QtWidgets.QPushButton('Copy to Clipboard', self)
        self.save_button = QtWidgets.QPushButton('Save to CSV File', self)

        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.save_button.clicked.connect(self.save_to_file)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table)
        # layout.addWidget(self.text_area)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.save_button)

        self.resize(self.default_width, self.default_height)
        self.setStyleSheet(style.load_stylesheet())

        overlay_widget = OverlayWidget(self)
        overlay_widget.project_selected.connect(self._on_project_select)
        self._overlay_widget = overlay_widget

    def _on_project_select(self, project_name: str):
        """Generate table when project is selected.

        This will generate the table and fill it with data.
        Source data are held in memory in `_result` attribute that
        is used to transform them into clipboard or csv file.
        """
        self._project_name = project_name
        self.process()
        if not self._result:
            self.set_content("no result generated")
            return

        rows = sum(len(value) for key, value in self._result.items())
        self.table.setRowCount(rows)

        row = 0
        content = []
        for key, value in self._result.items():
            item = QtWidgets.QTableWidgetItem(key)
            # this doesn't work as it is probably overriden by stylesheet?
            # item.setBackground(QColor(32, 32, 32))
            self.table.setItem(row, 0, item)
            for source in value:
                self.table.setItem(
                    row, 1, QtWidgets.QTableWidgetItem(source["name"]))
                self.table.setItem(
                    row, 2, QtWidgets.QTableWidgetItem(
                        str(source["version"])))
                row += 1

            # generate clipboard content
            content.append(key)
            content.extend(
                f"\t{source['name']} (v{source['version']})" for source in value  # noqa: E501
            )
        self.set_content("\n".join(content))

    def copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self._content, QClipboard.Clipboard)

    def save_to_file(self):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File')
        if file_name:
            self._write_csv(file_name)

    def set_content(self, content):
        self._content = content

    def get_content(self):
        return self._content

    def _resize_overlay(self):
        self._overlay_widget.resize(
            self.width(),
            self.height()
        )

    def resizeEvent(self, event):
        super(AssetReporterWindow, self).resizeEvent(event)
        self._resize_overlay()

    def _get_subset(self, version_id, project: Collection):
        pipeline = [
            {
                "$match": {
                    "_id": version_id
                },
            }, {
                "$lookup": {
                    "from": project.name,
                    "localField": "parent",
                    "foreignField": "_id",
                    "as": "parents"
                }
            }
        ]

        result = project.aggregate(pipeline)
        doc = next(result)
        # print(doc)
        return {
            "name": f'{"/".join(doc["parents"][0]["data"]["parents"])}/{doc["parents"][0]["name"]}/{doc["name"]}',  # noqa: E501
            "family": doc["data"].get("family") or doc["data"].get("families")[0]  # noqa: E501
        }

    def process(self):
        """Generate asset usage report data.

        This is the main method of the tool. It is using MongoDB
        aggregation pipeline to find all published versions that
        are used as input for other published versions. Then it
        generates a map of assets and their usage.

        """
        start = time.perf_counter()
        project = self._project_name

        # get all versions of published workfiles that has non-empty
        # inputLinks and connect it with their respective documents
        # using ID.
        pipeline = [
            {
                "$match": {
                    "data.inputLinks": {
                        "$exists": True,
                        "$ne": []
                    },
                    "data.families": {"$in": ["workfile"]}
                }
            }, {
                "$lookup": {
                    "from": project,
                    "localField": "data.inputLinks.id",
                    "foreignField": "_id",
                    "as": "linked_docs"
                }
            }
        ]

        client = OpenPypeMongoConnection.get_mongo_client()
        db = client["avalon"]

        result = db[project].aggregate(pipeline)

        asset_map = []
        # this is creating the map - for every workfile and its linked
        # documents, create a dictionary with "source" and "refs" keys
        # and resolve the subset name and version from the document
        for doc in result:
            source = {
                "source": self._get_subset(doc["parent"], db[project]),
            }
            source["source"].update({"version": doc["name"]})
            refs = []
            version = '<unknown>'
            for linked in doc["linked_docs"]:
                try:
                    version = f'v{linked["name"]}'
                except KeyError:
                    if linked["type"] == "hero_version":
                        version = "hero"
                finally:
                    refs.append({
                        "subset": self._get_subset(
                            linked["parent"], db[project]),
                        "version": version
                    })

            source["refs"] = refs
            asset_map.append(source)

        grouped = {}

        # this will group the assets by subset name and version
        for asset in asset_map:
            for ref in asset["refs"]:
                key = f'{ref["subset"]["name"]} ({ref["version"]})'
                if key in grouped:
                    grouped[key].append(asset["source"])
                else:
                    grouped[key] = [asset["source"]]
        self._result = grouped

        end = time.perf_counter()

        print(f"Finished in {end - start:0.4f} seconds", 2)

    def _write_csv(self, file_name: str) -> None:
        """Write CSV file with results."""
        with open(file_name, "w", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=";")
            writer.writerow(["Subset", "Used in", "Version"])
            for key, value in self._result.items():
                writer.writerow([key, "", ""])
                for source in value:
                    writer.writerow(["", source["name"], source["version"]])


def main():
    app_instance = get_openpype_qt_app()
    window = AssetReporterWindow()
    window.show()
    app_instance.exec_()


if __name__ == "__main__":
    main()
