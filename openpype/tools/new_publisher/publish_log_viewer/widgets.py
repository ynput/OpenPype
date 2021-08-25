import copy
import uuid

from Qt import QtWidgets, QtCore, QtGui

import pyblish.api

ITEM_ID_ROLE = QtCore.Qt.UserRole + 1
ITEM_IS_GROUP_ROLE = QtCore.Qt.UserRole + 2
PLUGIN_SKIPPED_ROLE = QtCore.Qt.UserRole + 3
PLUGIN_ERRORED_ROLE = QtCore.Qt.UserRole + 4
INSTANCE_REMOVED_ROLE = QtCore.Qt.UserRole + 5


class PluginItem:
    def __init__(self, plugin_data):
        self._id = uuid.uuid4()

        self.name = plugin_data["name"]
        self.label = plugin_data["label"]
        self.order = plugin_data["order"]
        self.skipped = plugin_data["skipped"]

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
                item.setData(instance_item.removed, INSTANCE_REMOVED_ROLE)
                item.setData(False, ITEM_IS_GROUP_ROLE)
                items.append(item)

            if family is None:
                family_items.extend(items)
                continue

            family_item = QtGui.QStandardItem(family)
            family_item.setFlags(QtCore.Qt.ItemIsEnabled)
            family_item.setData(True, ITEM_IS_GROUP_ROLE)
            family_item.appendRows(items)
            family_items.append(family_item)

        root_item.appendRows(family_items)


class InstanceProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(InstanceProxyModel, self).__init__(*args, **kwargs)

        self._ignore_removed = True

    @property
    def ignore_removed(self):
        return self._ignore_removed

    def set_ignore_removed(self, value):
        if value == self._ignore_removed:
            return
        self._ignore_removed = value

        if self.sourceModel():
            self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        source_index = model.index(row, 0, parent)
        if source_index.data(ITEM_IS_GROUP_ROLE):
            return model.rowCount(source_index) > 0

        if self._ignore_removed and source_index.data(PLUGIN_SKIPPED_ROLE):
            return False
        return True


class PluginsModel(QtGui.QStandardItemModel):
    order_label_mapping = (
        (pyblish.api.CollectorOrder + 0.5, "Collect"),
        (pyblish.api.ValidatorOrder + 0.5, "Validate"),
        (pyblish.api.ExtractorOrder + 0.5, "Extract"),
        (pyblish.api.IntegratorOrder + 0.5, "Integrate"),
        (None, "Other")
    )

    def set_report(self, report_item):
        self.clear()

        root_item = self.invisibleRootItem()

        labels_iter = iter(self.order_label_mapping)
        cur_order, cur_label = next(labels_iter)
        cur_plugin_items = []

        plugin_items_by_group_labels = []
        plugin_items_by_group_labels.append((cur_label, cur_plugin_items))
        for plugin_id in report_item.plugins_id_order:
            plugin_item = report_item.plugins_items_by_id[plugin_id]
            if cur_order is not None and plugin_item.order >= cur_order:
                cur_order, cur_label = next(labels_iter)
                cur_plugin_items = []
                plugin_items_by_group_labels.append(
                    (cur_label, cur_plugin_items)
                )

            cur_plugin_items.append(plugin_item)

        group_items = []
        for group_label, plugin_items in plugin_items_by_group_labels:
            group_item = QtGui.QStandardItem(group_label)
            group_item.setData(True, ITEM_IS_GROUP_ROLE)
            group_item.setFlags(QtCore.Qt.ItemIsEnabled)
            group_items.append(group_item)

            if not plugin_items:
                continue

            items = []
            for plugin_item in plugin_items:
                item = QtGui.QStandardItem(plugin_item.label)
                item.setData(False, ITEM_IS_GROUP_ROLE)
                item.setData(False, ITEM_IS_GROUP_ROLE)
                item.setData(plugin_item.id, ITEM_ID_ROLE)
                item.setData(plugin_item.skipped, PLUGIN_SKIPPED_ROLE)
                item.setData(plugin_item.errored, PLUGIN_ERRORED_ROLE)
                items.append(item)
            group_item.appendRows(items)

        root_item.appendRows(group_items)


class PluginProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(PluginProxyModel, self).__init__(*args, **kwargs)

        self._ignore_skipped = True

    @property
    def ignore_skipped(self):
        return self._ignore_skipped

    def set_ignore_skipped(self, value):
        if value == self._ignore_skipped:
            return
        self._ignore_skipped = value

        if self.sourceModel():
            self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        source_index = model.index(row, 0, parent)
        if source_index.data(ITEM_IS_GROUP_ROLE):
            return model.rowCount(source_index) > 0

        if self._ignore_skipped and source_index.data(PLUGIN_SKIPPED_ROLE):
            return False
        return True


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


class PublishLogViewerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PublishLogViewerWidget, self).__init__(parent)

        instances_model = InstancesModel()
        instances_proxy = InstanceProxyModel()
        instances_proxy.setSourceModel(instances_model)

        plugins_model = PluginsModel()
        plugins_proxy = PluginProxyModel()
        plugins_proxy.setSourceModel(plugins_model)

        removed_instances_check = QtWidgets.QCheckBox(
            "Hide removed instances", self
        )
        removed_instances_check.setChecked(instances_proxy.ignore_removed)

        instances_view = QtWidgets.QTreeView(self)
        instances_view.setModel(instances_proxy)
        # instances_view.setIndentation(0)
        instances_view.setHeaderHidden(True)
        instances_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)

        skipped_plugins_check = QtWidgets.QCheckBox(
            "Hide skipped plugins", self
        )
        skipped_plugins_check.setChecked(plugins_proxy.ignore_skipped)

        plugins_view = QtWidgets.QTreeView(self)
        plugins_view.setModel(plugins_proxy)
        # plugins_view.setIndentation(0)
        plugins_view.setHeaderHidden(True)
        plugins_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)

        details_widget = DetailsWidget(self)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(removed_instances_check, 0, 0)
        layout.addWidget(instances_view, 1, 0)
        layout.addWidget(skipped_plugins_check, 0, 1)
        layout.addWidget(plugins_view, 1, 1)
        layout.addWidget(details_widget, 1, 2)

        instances_view.selectionModel().selectionChanged.connect(
            self._on_instance_change
        )
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

        self._skipped_plugins_check = skipped_plugins_check
        self._plugins_view = plugins_view
        self._plugins_model = plugins_model
        self._plugins_proxy = plugins_proxy

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
