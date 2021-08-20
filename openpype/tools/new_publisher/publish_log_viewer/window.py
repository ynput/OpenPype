import os
import sys
import json
import collections

openpype_dir = r"C:\Users\jakub.trllo\Desktop\pype\pype3"
mongo_url = "mongodb://localhost:2707"

os.environ["OPENPYPE_MONGO"] = mongo_url
os.environ["AVALON_MONGO"] = mongo_url
os.environ["OPENPYPE_DATABASE_NAME"] = "openpype"
os.environ["AVALON_CONFIG"] = "openpype"
os.environ["AVALON_TIMEOUT"] = "1000"
os.environ["AVALON_DB"] = "avalon"
for path in [
    openpype_dir,
    r"{}\repos\avalon-core".format(openpype_dir),
    r"{}\.venv\Lib\site-packages".format(openpype_dir)
]:
    sys.path.append(path)

from Qt import QtWidgets, QtGui


class InstancesModel(QtGui.QStandardItemModel):
    def set_report(self, report_data):
        self.clear()

        root_item = self.invisibleRootItem()

        context_data = report_data["context"]
        context_label = context_data["label"] or "Context"

        context_item = QtGui.QStandardItem(context_label)

        items = [context_item]
        families = []
        instances_by_family = collections.defaultdict(list)
        instances_by_id = {}
        for instance_id, instance_detail in report_data["instances"].items():
            family = instance_detail["family"]
            if family not in families:
                families.append(family)

            label = instance_detail["label"] or instance_detail["name"]

            instance_item = QtGui.QStandardItem(label)
            instances_by_id[instance_id] = instance_item
            instances_by_family[family].append(instance_item)

        for family in families:
            instance_items = instances_by_family[family]
            family_item = QtGui.QStandardItem(family)
            family_item.appendRows(instance_items)
            items.append(family_item)

        root_item.appendRows(items)


class PluginsModel(QtGui.QStandardItemModel):
    def set_report(self, report_data):
        self.clear()

        plugins_data = report_data["plugins_data"]

        root_item = self.invisibleRootItem()

        items = []
        for plugin_detail in plugins_data:
            item = QtGui.QStandardItem(plugin_detail["label"])
            items.append(item)

        root_item.appendRows(items)


class PublishLogViewerWindow(QtWidgets.QWidget):
    default_width = 1000
    default_height = 600

    def __init__(self, parent=None):
        super(PublishLogViewerWindow, self).__init__(parent)

        instances_model = InstancesModel()
        plugins_model = PluginsModel()

        instances_view = QtWidgets.QTreeView(self)
        instances_view.setModel(instances_model)

        plugins_view = QtWidgets.QTreeView(self)
        plugins_view.setModel(plugins_model)

        views_layout = QtWidgets.QHBoxLayout()
        views_layout.addWidget(instances_view)
        views_layout.addWidget(plugins_view)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addLayout(views_layout)

        self.resize(self.default_width, self.default_height)

        self._instances_view = instances_view
        self._plugins_view = plugins_view

        self._instances_model = instances_model
        self._plugins_model = plugins_model

        log_path = os.path.join(os.path.dirname(__file__), "logs.json")
        with open(log_path, "r") as file_stream:
            report_data = json.load(file_stream)

        plugins_model.set_report(report_data)
        instances_model.set_report(report_data)


def main():
    """Main function for testing purposes."""
    app = QtWidgets.QApplication([])
    window = PublishLogViewerWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
