import os
import sys
import json
import copy
import uuid
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

from Qt import QtWidgets, QtCore, QtGui

from openpype import style

ITEM_ID_ROLE = QtCore.Qt.UserRole + 1


class PluginItem:
    def __init__(self, plugin_data):
        self._id = uuid.uuid4()

        self.name = plugin_data["name"]
        self.label = plugin_data["label"]
        self.order = plugin_data["order"]
        self.skipped = plugin_data["skipped"]

        logs = []
        for instance_data in plugin_data["instances_data"]:
            logs.extend(copy.deepcopy(instance_data["logs"]))

        self.logs = logs

    @property
    def id(self):
        return self._id


class InstanceItem:
    def __init__(self, instance_id, instance_data, report_data):
        self._id = instance_id
        self.label = instance_data.get("label") or instance_data.get("name")
        self.family = instance_data.get("family")

        logs = []
        for plugin_data in report_data["plugins_data"]:
            for instance_data_item in plugin_data["instances_data"]:
                if instance_data_item["id"] == self._id:
                    logs.extend(copy.deepcopy(instance_data_item["logs"]))

        self.logs = logs

    @property
    def id(self):
        return self._id


class PublishReport:
    def __init__(self, report_data):
        data = copy.deepcopy(report_data)

        context_data = data["context"]
        context_data["name"] = "context"
        context_data["label"] = context_data["label"] or "Context"

        instance_items_by_id = {}
        instance_items_by_family = {}
        context_item = InstanceItem(None, context_data, data)
        instance_items_by_id[context_item.id] = context_item
        instance_items_by_family[context_item.family] = [context_item]

        for instance_id, instance_data in data["instances"].items():
            item = InstanceItem(instance_id, instance_data, data)
            instance_items_by_id[item.id] = item
            if item.family not in instance_items_by_family:
                instance_items_by_family[item.family] = []
            instance_items_by_family[item.family].append(item)

        all_logs = []
        plugins_items_by_id = {}
        plugins_id_order = []
        for plugin_data in data["plugins_data"]:
            item = PluginItem(plugin_data)
            plugins_id_order.append(item.id)
            plugins_items_by_id[item.id] = item
            all_logs.extend(copy.deepcopy(item.logs))

        self.instance_items_by_id = instance_items_by_id
        self.instance_items_by_family = instance_items_by_family

        self.plugins_id_order = plugins_id_order
        self.plugins_items_by_id = plugins_items_by_id

        self.logs = all_logs


class InstancesModel(QtGui.QStandardItemModel):
    def set_report(self, report_item):
        self.clear()

        root_item = self.invisibleRootItem()

        families = set(report_item.instance_items_by_family.keys())
        families.remove(None)
        all_families = list(sorted(families))
        all_families.insert(0, None)

        family_items = []
        for family in all_families:
            items = []
            instance_items = report_item.instance_items_by_family[family]
            for instance_item in instance_items:
                item = QtGui.QStandardItem(instance_item.label)
                item.setData(instance_item.id, ITEM_ID_ROLE)
                items.append(item)

            if family is None:
                family_items.extend(items)
                continue

            family_item = QtGui.QStandardItem(family)
            family_item.appendRows(items)
            family_items.append(family_item)

        root_item.appendRows(family_items)


class PluginsModel(QtGui.QStandardItemModel):
    def set_report(self, report_item):
        self.clear()

        root_item = self.invisibleRootItem()

        items = []
        for plugin_id in report_item.plugins_id_order:
            plugin_item = report_item.plugins_items_by_id[plugin_id]
            item = QtGui.QStandardItem(plugin_item.label)
            item.setData(plugin_item.id, ITEM_ID_ROLE)
            items.append(item)

        root_item.appendRows(items)


class DetailsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(DetailsWidget, self).__init__(parent)

        output_widget = QtWidgets.QPlainTextEdit(self)
        output_widget.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        output_widget.setObjectName("PublishLogConsole")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(output_widget)

        self._output_widget = output_widget

    def clear(self):
        self._output_widget.setPlainText("")

    def set_logs(self, logs):
        lines = []
        for log in logs:
            if log["type"] == "record":
                message = "{}: {}".format(log["levelname"], log["msg"])

                lines.append(message)
                exc_info = log["exc_info"]
                if exc_info:
                    lines.append(exc_info)

            else:
                print(log["type"])

        text = "\n".join(lines)
        self._output_widget.setPlainText(text)


class PublishLogViewerWindow(QtWidgets.QWidget):
    default_width = 1200
    default_height = 600

    def __init__(self, parent=None):
        super(PublishLogViewerWindow, self).__init__(parent)

        instances_model = InstancesModel()
        plugins_model = PluginsModel()

        instances_view = QtWidgets.QTreeView(self)
        instances_view.setModel(instances_model)
        # instances_view.setIndentation(0)
        instances_view.setHeaderHidden(True)
        instances_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)

        plugins_view = QtWidgets.QTreeView(self)
        plugins_view.setModel(plugins_model)
        # plugins_view.setIndentation(0)
        plugins_view.setHeaderHidden(True)
        plugins_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)

        details_widget = DetailsWidget(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(instances_view)
        layout.addWidget(plugins_view)
        layout.addWidget(details_widget, 1)

        instances_view.selectionModel().selectionChanged.connect(
            self._on_instance_change
        )
        plugins_view.selectionModel().selectionChanged.connect(
            self._on_plugin_change
        )

        self._ignore_selection_changes = False
        self._report_item = None
        self._details_widget = details_widget

        self._instances_view = instances_view
        self._plugins_view = plugins_view

        self._instances_model = instances_model
        self._plugins_model = plugins_model

        self.resize(self.default_width, self.default_height)
        self.setStyleSheet(style.load_stylesheet())

    def _on_instance_change(self, *_args):
        if self._ignore_selection_changes:
            return

        valid_index = None
        for index in self._instances_view.selectedIndexes():
            if index.isValid():
                valid_index = index
                break

        if valid_index is None:
            print("NOT INSTANCE")
            return

        if self._plugins_view.selectedIndexes():
            self._ignore_selection_changes = True
            self._plugins_view.selectionModel().clearSelection()
            self._ignore_selection_changes = False

        plugin_id = valid_index.data(ITEM_ID_ROLE)
        instance_item = self._report_item.instance_items_by_id[plugin_id]
        self._details_widget.set_logs(instance_item.logs)

    def _on_plugin_change(self, *_args):
        if self._ignore_selection_changes:
            return

        valid_index = None
        for index in self._plugins_view.selectedIndexes():
            if index.isValid():
                valid_index = index
                break

        if valid_index is None:
            self._details_widget.set_logs(self._report_item.logs)
            return

        if self._instances_view.selectedIndexes():
            self._ignore_selection_changes = True
            self._instances_view.selectionModel().clearSelection()
            self._ignore_selection_changes = False

        plugin_id = valid_index.data(ITEM_ID_ROLE)
        plugin_item = self._report_item.plugins_items_by_id[plugin_id]
        self._details_widget.set_logs(plugin_item.logs)

    def set_report(self, report_data):
        self._ignore_selection_changes = True

        report_item = PublishReport(report_data)
        self._report_item = report_item

        self._instances_model.set_report(report_item)
        self._plugins_model.set_report(report_item)

        self._details_widget.set_logs(report_item.logs)

        self._ignore_selection_changes = False


def main():
    """Main function for testing purposes."""
    app = QtWidgets.QApplication([])
    window = PublishLogViewerWindow()

    log_path = os.path.join(os.path.dirname(__file__), "logs.json")
    with open(log_path, "r") as file_stream:
        report_data = json.load(file_stream)

    window.set_report(report_data)

    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
