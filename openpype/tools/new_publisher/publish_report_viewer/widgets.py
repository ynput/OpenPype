import copy
import uuid

from Qt import QtWidgets, QtCore

from openpype.widgets.nice_checkbox import NiceCheckbox

from .constants import (
    ITEM_ID_ROLE,
    ITEM_IS_GROUP_ROLE
)
from .delegates import GroupItemDelegate
from .model import (
    InstancesModel,
    InstanceProxyModel,
    PluginsModel,
    PluginProxyModel
)


class PluginItem:
    def __init__(self, plugin_data):
        self._id = uuid.uuid4()

        self.name = plugin_data["name"]
        self.label = plugin_data["label"]
        self.order = plugin_data["order"]
        self.skipped = plugin_data["skipped"]
        self.passed = plugin_data["passed"]

        logs = []
        errored = False
        for instance_data in plugin_data["instances_data"]:
            for log_item in instance_data["logs"]:
                if not errored:
                    errored = log_item["type"] == "error"
                logs.append(copy.deepcopy(log_item))

        self.errored = errored
        self.logs = logs

    @property
    def id(self):
        return self._id


class InstanceItem:
    def __init__(self, instance_id, instance_data, report_data):
        self._id = instance_id
        self.label = instance_data.get("label") or instance_data.get("name")
        self.family = instance_data.get("family")
        self.removed = not instance_data.get("exists", True)

        logs = []
        for plugin_data in report_data["plugins_data"]:
            for instance_data_item in plugin_data["instances_data"]:
                if instance_data_item["id"] == self._id:
                    logs.extend(copy.deepcopy(instance_data_item["logs"]))

        errored = False
        for log in logs:
            if log["type"] == "error":
                errored = True
                break

        self.errored = errored
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

            elif log["type"] == "error":
                lines.append(log["traceback"])

            else:
                print(log["type"])

        text = "\n".join(lines)
        self._output_widget.setPlainText(text)


class PublishReportViewerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PublishReportViewerWidget, self).__init__(parent)

        instances_model = InstancesModel()
        instances_proxy = InstanceProxyModel()
        instances_proxy.setSourceModel(instances_model)

        plugins_model = PluginsModel()
        plugins_proxy = PluginProxyModel()
        plugins_proxy.setSourceModel(plugins_model)

        removed_instances_check = NiceCheckbox(parent=self)
        removed_instances_check.setChecked(instances_proxy.ignore_removed)
        removed_instances_label = QtWidgets.QLabel(
            "Hide removed instances", self
        )

        removed_instances_layout = QtWidgets.QHBoxLayout()
        removed_instances_layout.setContentsMargins(0, 0, 0, 0)
        removed_instances_layout.addWidget(removed_instances_check, 0)
        removed_instances_layout.addWidget(removed_instances_label, 1)

        instances_view = QtWidgets.QTreeView(self)
        instances_view.setObjectName("PublishDetailViews")
        instances_view.setModel(instances_proxy)
        instances_view.setIndentation(0)
        instances_view.setHeaderHidden(True)
        instances_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        instances_view.setExpandsOnDoubleClick(False)

        instances_delegate = GroupItemDelegate(instances_view)
        instances_view.setItemDelegate(instances_delegate)

        skipped_plugins_check = NiceCheckbox(parent=self)
        skipped_plugins_check.setChecked(plugins_proxy.ignore_skipped)
        skipped_plugins_label = QtWidgets.QLabel("Hide skipped plugins", self)

        skipped_plugins_layout = QtWidgets.QHBoxLayout()
        skipped_plugins_layout.setContentsMargins(0, 0, 0, 0)
        skipped_plugins_layout.addWidget(skipped_plugins_check, 0)
        skipped_plugins_layout.addWidget(skipped_plugins_label, 1)

        plugins_view = QtWidgets.QTreeView(self)
        plugins_view.setObjectName("PublishDetailViews")
        plugins_view.setModel(plugins_proxy)
        plugins_view.setIndentation(0)
        plugins_view.setHeaderHidden(True)
        plugins_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        plugins_view.setExpandsOnDoubleClick(False)

        plugins_delegate = GroupItemDelegate(plugins_view)
        plugins_view.setItemDelegate(plugins_delegate)

        details_widget = DetailsWidget(self)

        layout = QtWidgets.QGridLayout(self)
        # Row 1
        layout.addLayout(removed_instances_layout, 0, 0)
        layout.addLayout(skipped_plugins_layout, 0, 1)
        # Row 2
        layout.addWidget(instances_view, 1, 0)
        layout.addWidget(plugins_view, 1, 1)
        layout.addWidget(details_widget, 1, 2)

        layout.setColumnStretch(2, 1)

        instances_view.selectionModel().selectionChanged.connect(
            self._on_instance_change
        )
        instances_view.clicked.connect(self._on_instance_view_clicked)
        plugins_view.clicked.connect(self._on_plugin_view_clicked)
        plugins_view.selectionModel().selectionChanged.connect(
            self._on_plugin_change
        )

        skipped_plugins_check.stateChanged.connect(
            self._on_skipped_plugin_check
        )
        removed_instances_check.stateChanged.connect(
            self._on_removed_instances_check
        )

        self._ignore_selection_changes = False
        self._report_item = None
        self._details_widget = details_widget

        self._removed_instances_check = removed_instances_check
        self._instances_view = instances_view
        self._instances_model = instances_model
        self._instances_proxy = instances_proxy

        self._instances_delegate = instances_delegate
        self._plugins_delegate = plugins_delegate

        self._skipped_plugins_check = skipped_plugins_check
        self._plugins_view = plugins_view
        self._plugins_model = plugins_model
        self._plugins_proxy = plugins_proxy

    def _on_instance_view_clicked(self, index):
        if not index.isValid() or not index.data(ITEM_IS_GROUP_ROLE):
            return

        if self._instances_view.isExpanded(index):
            self._instances_view.collapse(index)
        else:
            self._instances_view.expand(index)

    def _on_plugin_view_clicked(self, index):
        if not index.isValid() or not index.data(ITEM_IS_GROUP_ROLE):
            return

        if self._plugins_view.isExpanded(index):
            self._plugins_view.collapse(index)
        else:
            self._plugins_view.expand(index)

    def set_report(self, report_data):
        self._ignore_selection_changes = True

        report_item = PublishReport(report_data)
        self._report_item = report_item

        self._instances_model.set_report(report_item)
        self._plugins_model.set_report(report_item)
        self._details_widget.set_logs(report_item.logs)

        self._ignore_selection_changes = False

    def _on_instance_change(self, *_args):
        if self._ignore_selection_changes:
            return

        valid_index = None
        for index in self._instances_view.selectedIndexes():
            if index.isValid():
                valid_index = index
                break

        if valid_index is None:
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

    def _on_skipped_plugin_check(self):
        self._plugins_proxy.set_ignore_skipped(
            self._skipped_plugins_check.isChecked()
        )

    def _on_removed_instances_check(self):
        self._instances_proxy.set_ignore_removed(
            self._removed_instances_check.isChecked()
        )
