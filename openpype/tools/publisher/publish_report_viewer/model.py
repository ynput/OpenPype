import uuid
from Qt import QtCore, QtGui

import pyblish.api

from .constants import (
    ITEM_ID_ROLE,
    ITEM_IS_GROUP_ROLE,
    ITEM_LABEL_ROLE,
    ITEM_ERRORED_ROLE,
    PLUGIN_SKIPPED_ROLE,
    PLUGIN_PASSED_ROLE,
    INSTANCE_REMOVED_ROLE
)


class InstancesModel(QtGui.QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(InstancesModel, self).__init__(*args, **kwargs)

        self._items_by_id = {}
        self._plugin_items_by_id = {}

    def get_items_by_id(self):
        return self._items_by_id

    def set_report(self, report_item):
        self.clear()
        self._items_by_id.clear()
        self._plugin_items_by_id.clear()
        if not report_item:
            return

        root_item = self.invisibleRootItem()

        families = set(report_item.instance_items_by_family.keys())
        families.remove(None)
        all_families = list(sorted(families))
        all_families.insert(0, None)

        family_items = []
        for family in all_families:
            items = []
            instance_items = report_item.instance_items_by_family[family]
            all_removed = True
            for instance_item in instance_items:
                item = QtGui.QStandardItem(instance_item.label)
                item.setData(instance_item.label, ITEM_LABEL_ROLE)
                item.setData(instance_item.errored, ITEM_ERRORED_ROLE)
                item.setData(instance_item.id, ITEM_ID_ROLE)
                item.setData(instance_item.removed, INSTANCE_REMOVED_ROLE)
                if all_removed and not instance_item.removed:
                    all_removed = False
                item.setData(False, ITEM_IS_GROUP_ROLE)
                items.append(item)
                self._items_by_id[instance_item.id] = item
                self._plugin_items_by_id[instance_item.id] = item

            if family is None:
                family_items.extend(items)
                continue

            family_item = QtGui.QStandardItem(family)
            family_item.setData(family, ITEM_LABEL_ROLE)
            family_item.setFlags(QtCore.Qt.ItemIsEnabled)
            family_id = uuid.uuid4()
            family_item.setData(family_id, ITEM_ID_ROLE)
            family_item.setData(all_removed, INSTANCE_REMOVED_ROLE)
            family_item.setData(True, ITEM_IS_GROUP_ROLE)
            family_item.appendRows(items)
            family_items.append(family_item)
            self._items_by_id[family_id] = family_item

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
        source_index = self.sourceModel().index(row, 0, parent)
        if self._ignore_removed and source_index.data(INSTANCE_REMOVED_ROLE):
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

    def __init__(self, *args, **kwargs):
        super(PluginsModel, self).__init__(*args, **kwargs)

        self._items_by_id = {}
        self._plugin_items_by_id = {}

    def get_items_by_id(self):
        return self._items_by_id

    def set_report(self, report_item):
        self.clear()
        self._items_by_id.clear()
        self._plugin_items_by_id.clear()
        if not report_item:
            return

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
            group_id = uuid.uuid4()
            group_item = QtGui.QStandardItem(group_label)
            group_item.setData(group_label, ITEM_LABEL_ROLE)
            group_item.setData(group_id, ITEM_ID_ROLE)
            group_item.setData(True, ITEM_IS_GROUP_ROLE)
            group_item.setFlags(QtCore.Qt.ItemIsEnabled)
            group_items.append(group_item)

            self._items_by_id[group_id] = group_item

            if not plugin_items:
                continue

            items = []
            for plugin_item in plugin_items:
                item = QtGui.QStandardItem(plugin_item.label)
                item.setData(False, ITEM_IS_GROUP_ROLE)
                item.setData(plugin_item.label, ITEM_LABEL_ROLE)
                item.setData(plugin_item.id, ITEM_ID_ROLE)
                item.setData(plugin_item.skipped, PLUGIN_SKIPPED_ROLE)
                item.setData(plugin_item.passed, PLUGIN_PASSED_ROLE)
                item.setData(plugin_item.errored, ITEM_ERRORED_ROLE)
                items.append(item)
                self._items_by_id[plugin_item.id] = item
                self._plugin_items_by_id[plugin_item.id] = item
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
