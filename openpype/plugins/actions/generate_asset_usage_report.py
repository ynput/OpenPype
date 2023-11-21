"""
TODO: we need to move it to subprocess to show UI
"""
import csv
import os
import tempfile
import time

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtGui import QClipboard

from pymongo.collection import Collection

from openpype.client import OpenPypeMongoConnection
from openpype.pipeline import LauncherAction


class ReportWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.text_area = QtWidgets.QTextEdit(self)
        self.copy_button = QtWidgets.QPushButton('Copy to Clipboard', self)
        self.save_button = QtWidgets.QPushButton('Save to CSV File', self)

        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.save_button.clicked.connect(self.save_to_file)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.text_area)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.save_button)

    def copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.text_area.toPlainText(), QClipboard.Clipboard)

    def save_to_file(self):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File')
        if file_name:
            with open(file_name, 'w') as file:
                file.write(self.text_area.toPlainText())

    def set_content(self, content):
        self.text_area.setText(content)


class OpenTaskPath(LauncherAction):
    name = "get_asset_usage_report"
    label = "Asset Usage Report"
    icon = "list"
    order = 500

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        return bool(session.get("AVALON_ASSET"))

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
            "name": f'{"/".join(doc["parents"][0]["data"]["parents"])}/{doc["parents"][0]["name"]}/{doc["name"]}',
            "family": doc["data"].get("family") or doc["data"].get("families")[0]
        }

    def process(self, session, **kwargs):
        start = time.perf_counter()
        project = session["AVALON_PROJECT"]

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
                    "from": "OP01_CG_demo",
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
        for doc in result:
            source = {
                "source": self._get_subset(doc["parent"], db[project]),
            }
            source["source"].update({"version": doc["name"]})
            refs = [
                {
                    "subset": self._get_subset(linked["parent"], db[project]),
                    "version": linked.get("name")
                }
                for linked in doc["linked_docs"]
            ]
            source["refs"] = refs
            asset_map.append(source)

        # for ref in asset_map:
        #    print(ref)

        grouped = {}

        for asset in asset_map:
            for ref in asset["refs"]:
                key = f'{ref["subset"]["name"]} (v{ref["version"]})'
                if key in grouped:
                    grouped[key].append(asset["source"])
                else:
                    grouped[key] = [asset["source"]]

        temp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        try:
            with open(temp.name, "w", newline="") as csvfile:
                writer = csv.writer(csvfile, delimiter=";")
                writer.writerow(["Subset", "Used in", "Version"])
                for key, value in grouped.items():
                    writer.writerow([key, "", ""])
                    for source in value:
                        writer.writerow(["", source["name"], source["version"]])
        finally:
            temp.close()

        end = time.perf_counter()
        app = QtWidgets.QApplication.instance()
        window = ReportWindow()
        # window.set_content(open(temp.name).read())
        window.show()
        print(f"Finished in {end - start:0.4f} seconds", 2)
