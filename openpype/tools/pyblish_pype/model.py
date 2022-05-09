"""Qt models

Description:
    The model contains the original objects from Pyblish, such as
    pyblish.api.Instance and pyblish.api.Plugin. The model then
    provides an interface for reading and writing to those.

GUI data:
    Aside from original data, such as pyblish.api.Plugin.optional,
    the GUI also hosts data internal to itself, such as whether or
    not an item has processed such that it may be colored appropriately
    in the view. This data is prefixed with two underscores (__).

    E.g.

    _has_processed

    This is so that the the GUI-only data doesn't accidentally overwrite
    or cause confusion with existing data in plug-ins and instances.

Roles:
    Data is accessed via standard Qt "roles". You can think of a role
    as the key of a dictionary, except they can only be integers.

"""
from __future__ import unicode_literals

import pyblish

from . import settings, util
from .awesome import tags as awesome
from Qt import QtCore, QtGui
import qtawesome
from six import text_type
from .constants import PluginStates, InstanceStates, GroupStates, Roles

from openpype.api import get_system_settings


# ItemTypes
InstanceType = QtGui.QStandardItem.UserType
PluginType = QtGui.QStandardItem.UserType + 1
GroupType = QtGui.QStandardItem.UserType + 2
TerminalLabelType = QtGui.QStandardItem.UserType + 3
TerminalDetailType = QtGui.QStandardItem.UserType + 4


class QAwesomeTextIconFactory:
    icons = {}

    @classmethod
    def icon(cls, icon_name):
        if icon_name not in cls.icons:
            cls.icons[icon_name] = awesome.get(icon_name)
        return cls.icons[icon_name]


class QAwesomeIconFactory:
    icons = {}

    @classmethod
    def icon(cls, icon_name, icon_color):
        if icon_name not in cls.icons:
            cls.icons[icon_name] = {}

        if icon_color not in cls.icons[icon_name]:
            cls.icons[icon_name][icon_color] = qtawesome.icon(
                icon_name,
                color=icon_color
            )
        return cls.icons[icon_name][icon_color]


class IntentModel(QtGui.QStandardItemModel):
    """Model for QComboBox with intents.

    It is expected that one inserted item is dictionary.
    Key represents #Label and Value represent #Value.

    Example:
    {
        "Testing": "test",
        "Publishing": "publish"
    }

    First and default value is {"< Not Set >": None}
    """

    default_item = {"< Not Set >": None}

    def __init__(self, parent=None):
        super(IntentModel, self).__init__(parent)
        self._item_count = 0
        self.default_index = 0

    @property
    def has_items(self):
        return self._item_count > 0

    def reset(self):
        self.clear()
        self._item_count = 0
        self.default_index = 0

        intents_preset = (
            get_system_settings()
            .get("modules", {})
            .get("ftrack", {})
            .get("intent", {})
        )

        default = intents_preset.get("default")
        items = intents_preset.get("items", {})
        if not items:
            return

        for idx, item_value in enumerate(items.keys()):
            if item_value == default:
                self.default_index = idx
                break

        self.add_items(items)

    def add_items(self, items):
        for value, label in items.items():
            new_item = QtGui.QStandardItem()
            new_item.setData(label, QtCore.Qt.DisplayRole)
            new_item.setData(value, Roles.IntentItemValue)

            self.setItem(self._item_count, new_item)
            self._item_count += 1


class PluginItem(QtGui.QStandardItem):
    """Plugin item implementation."""

    def __init__(self, plugin):
        super(PluginItem, self).__init__()

        item_text = plugin.__name__
        if settings.UseLabel:
            if hasattr(plugin, "label") and plugin.label:
                item_text = plugin.label

        self.plugin = plugin

        self.setData(item_text, QtCore.Qt.DisplayRole)
        self.setData(False, Roles.IsEnabledRole)
        self.setData(0, Roles.PublishFlagsRole)
        self.setData(0, Roles.PluginActionProgressRole)
        icon_name = ""
        if hasattr(plugin, "icon") and plugin.icon:
            icon_name = plugin.icon
        icon = QAwesomeTextIconFactory.icon(icon_name)
        self.setData(icon, QtCore.Qt.DecorationRole)

        actions = []
        if hasattr(plugin, "actions") and plugin.actions:
            actions = list(plugin.actions)
        plugin.actions = actions

        is_checked = True
        is_optional = getattr(plugin, "optional", False)
        if is_optional:
            is_checked = getattr(plugin, "active", True)

        plugin.active = is_checked
        plugin.optional = is_optional

        self.setData(
            "{}.{}".format(plugin.__module__, plugin.__name__),
            Roles.ObjectUIdRole
        )

        self.setFlags(
            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        )

    def type(self):
        return PluginType

    def data(self, role=QtCore.Qt.DisplayRole):
        if role == Roles.IsOptionalRole:
            return self.plugin.optional

        if role == Roles.ObjectIdRole:
            return self.plugin.id

        if role == Roles.TypeRole:
            return self.type()

        if role == QtCore.Qt.CheckStateRole:
            return self.plugin.active

        if role == Roles.PathModuleRole:
            return self.plugin.__module__

        if role == Roles.FamiliesRole:
            return self.plugin.families

        if role == Roles.DocstringRole:
            return self.plugin.__doc__

        if role == Roles.PluginActionsVisibleRole:
            return self._data_actions_visible()

        if role == Roles.PluginValidActionsRole:
            return self._data_valid_actions()

        return super(PluginItem, self).data(role)

    def _data_actions_visible(self):
        # Can only run actions on active plug-ins.
        if not self.plugin.active or not self.plugin.actions:
            return False

        publish_states = self.data(Roles.PublishFlagsRole)
        if (
            not publish_states & PluginStates.IsCompatible
            or publish_states & PluginStates.WasSkipped
        ):
            return False

        # Context specific actions
        for action in self.plugin.actions:
            if action.on == "failed":
                if publish_states & PluginStates.HasError:
                    return True

            elif action.on == "succeeded":
                if (
                    publish_states & PluginStates.WasProcessed
                    and not publish_states & PluginStates.HasError
                ):
                    return True

            elif action.on == "processed":
                if publish_states & PluginStates.WasProcessed:
                    return True

            elif action.on == "notProcessed":
                if not publish_states & PluginStates.WasProcessed:
                    return True
        return False

    def _data_valid_actions(self):
        valid_actions = []

        # Can only run actions on active plug-ins.
        if not self.plugin.active or not self.plugin.actions:
            return valid_actions

        if not self.plugin.active or not self.plugin.actions:
            return False

        publish_states = self.data(Roles.PublishFlagsRole)
        if (
            not publish_states & PluginStates.IsCompatible
            or publish_states & PluginStates.WasSkipped
        ):
            return False

        # Context specific actions
        for action in self.plugin.actions:
            valid = False
            if action.on == "failed":
                if publish_states & PluginStates.HasError:
                    valid = True

            elif action.on == "succeeded":
                if (
                    publish_states & PluginStates.WasProcessed
                    and not publish_states & PluginStates.HasError
                ):
                    valid = True

            elif action.on == "processed":
                if publish_states & PluginStates.WasProcessed:
                    valid = True

            elif action.on == "notProcessed":
                if not publish_states & PluginStates.WasProcessed:
                    valid = True

            if valid:
                valid_actions.append(action)

        if not valid_actions:
            return valid_actions

        actions_len = len(valid_actions)
        # Discard empty groups
        indexex_to_remove = []
        for idx, action in enumerate(valid_actions):
            if action.__type__ != "category":
                continue

            next_id = idx + 1
            if next_id >= actions_len:
                indexex_to_remove.append(idx)
                continue

            next = valid_actions[next_id]
            if next.__type__ != "action":
                indexex_to_remove.append(idx)

        for idx in reversed(indexex_to_remove):
            valid_actions.pop(idx)

        return valid_actions

    def setData(self, value, role=None):
        if role is None:
            role = QtCore.Qt.UserRole + 1

        if role == QtCore.Qt.CheckStateRole:
            if not self.data(Roles.IsEnabledRole):
                return False
            self.plugin.active = value
            self.emitDataChanged()
            return

        elif role == Roles.PluginActionProgressRole:
            if isinstance(value, list):
                _value = self.data(Roles.PluginActionProgressRole)
                for flag in value:
                    _value |= flag
                value = _value

            elif isinstance(value, dict):
                _value = self.data(Roles.PluginActionProgressRole)
                for flag, _bool in value.items():
                    if _bool is True:
                        _value |= flag
                    elif _value & flag:
                        _value ^= flag
                value = _value

        elif role == Roles.PublishFlagsRole:
            if isinstance(value, list):
                _value = self.data(Roles.PublishFlagsRole)
                for flag in value:
                    _value |= flag
                value = _value

            elif isinstance(value, dict):
                _value = self.data(Roles.PublishFlagsRole)
                for flag, _bool in value.items():
                    if _bool is True:
                        _value |= flag
                    elif _value & flag:
                        _value ^= flag
                value = _value

            if value & PluginStates.HasWarning:
                if self.parent():
                    self.parent().setData(
                        {GroupStates.HasWarning: True},
                        Roles.PublishFlagsRole
                    )
            if value & PluginStates.HasError:
                if self.parent():
                    self.parent().setData(
                        {GroupStates.HasError: True},
                        Roles.PublishFlagsRole
                    )

        return super(PluginItem, self).setData(value, role)


class GroupItem(QtGui.QStandardItem):
    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop("order", None)
        self.publish_states = 0
        super(GroupItem, self).__init__(*args, **kwargs)

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def data(self, role=QtCore.Qt.DisplayRole):
        if role == Roles.PublishFlagsRole:
            return self.publish_states

        if role == Roles.TypeRole:
            return self.type()

        return super(GroupItem, self).data(role)

    def setData(self, value, role=(QtCore.Qt.UserRole + 1)):
        if role == Roles.PublishFlagsRole:
            if isinstance(value, list):
                _value = self.data(Roles.PublishFlagsRole)
                for flag in value:
                    _value |= flag
                value = _value

            elif isinstance(value, dict):
                _value = self.data(Roles.PublishFlagsRole)
                for flag, _bool in value.items():
                    if _bool is True:
                        _value |= flag
                    elif _value & flag:
                        _value ^= flag
                value = _value
            self.publish_states = value
            self.emitDataChanged()
            return True

        return super(GroupItem, self).setData(value, role)

    def type(self):
        return GroupType


class PluginModel(QtGui.QStandardItemModel):
    def __init__(self, controller, *args, **kwargs):
        super(PluginModel, self).__init__(*args, **kwargs)

        self.controller = controller
        self.checkstates = {}
        self.group_items = {}
        self.plugin_items = {}

    def reset(self):
        self.group_items = {}
        self.plugin_items = {}
        self.clear()

    def append(self, plugin):
        plugin_groups = self.controller.order_groups.groups
        label = None
        order = None
        for _order, item in reversed(plugin_groups.items()):
            if _order is None or plugin.order < _order:
                label = item["label"]
                order = _order
            else:
                break

        if label is None:
            label = "Other"

        group_item = self.group_items.get(label)
        if not group_item:
            group_item = GroupItem(label, order=order)
            self.appendRow(group_item)
            self.group_items[label] = group_item

        new_item = PluginItem(plugin)
        group_item.appendRow(new_item)

        self.plugin_items[plugin._id] = new_item

    def store_checkstates(self):
        self.checkstates.clear()

        for plugin_item in self.plugin_items.values():
            if not plugin_item.plugin.optional:
                continue

            uid = plugin_item.data(Roles.ObjectUIdRole)
            self.checkstates[uid] = plugin_item.data(QtCore.Qt.CheckStateRole)

    def restore_checkstates(self):
        for plugin_item in self.plugin_items.values():
            if not plugin_item.plugin.optional:
                continue

            uid = plugin_item.data(Roles.ObjectUIdRole)
            state = self.checkstates.get(uid)
            if state is not None:
                plugin_item.setData(state, QtCore.Qt.CheckStateRole)

    def update_with_result(self, result):
        plugin = result["plugin"]
        item = self.plugin_items[plugin.id]

        new_flag_states = {
            PluginStates.InProgress: False,
            PluginStates.WasProcessed: True
        }

        publish_states = item.data(Roles.PublishFlagsRole)

        has_warning = publish_states & PluginStates.HasWarning
        new_records = result.get("records") or []
        if not has_warning:
            for record in new_records:
                level_no = record.get("levelno")
                if level_no and level_no >= 30:
                    new_flag_states[PluginStates.HasWarning] = True
                    break

        if (
            not publish_states & PluginStates.HasError
            and not result["success"]
        ):
            new_flag_states[PluginStates.HasError] = True

        if not publish_states & PluginStates.IsCompatible:
            new_flag_states[PluginStates.IsCompatible] = True

        item.setData(new_flag_states, Roles.PublishFlagsRole)

        records = item.data(Roles.LogRecordsRole) or []
        records.extend(new_records)

        item.setData(records, Roles.LogRecordsRole)

        return item

    def update_compatibility(self):
        context = self.controller.context

        families = util.collect_families_from_instances(context, True)
        for plugin_item in self.plugin_items.values():
            publish_states = plugin_item.data(Roles.PublishFlagsRole)
            if (
                publish_states & PluginStates.WasProcessed
                or publish_states & PluginStates.WasSkipped
            ):
                continue

            is_compatible = False
            # A plugin should always show if it has processed.
            if plugin_item.plugin.__instanceEnabled__:
                compatible_instances = pyblish.logic.instances_by_plugin(
                    context, plugin_item.plugin
                )
                for instance in context:
                    if not instance.data.get("publish"):
                        continue

                    if instance in compatible_instances:
                        is_compatible = True
                        break
            else:
                plugins = pyblish.logic.plugins_by_families(
                    [plugin_item.plugin], families
                )
                if plugins:
                    is_compatible = True

            current_is_compatible = publish_states & PluginStates.IsCompatible
            if (
                (is_compatible and not current_is_compatible)
                or (not is_compatible and current_is_compatible)
            ):
                new_flag = {
                    PluginStates.IsCompatible: is_compatible
                }
                plugin_item.setData(new_flag, Roles.PublishFlagsRole)


class PluginFilterProxy(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        item_type = index.data(Roles.TypeRole)
        if item_type != PluginType:
            return True

        publish_states = index.data(Roles.PublishFlagsRole)
        if (
            publish_states & PluginStates.WasSkipped
            or not publish_states & PluginStates.IsCompatible
        ):
            return False
        return True


class InstanceItem(QtGui.QStandardItem):
    """Instance item implementation."""

    def __init__(self, instance):
        super(InstanceItem, self).__init__()

        self.instance = instance
        self.is_context = False
        publish_states = getattr(instance, "_publish_states", 0)
        if publish_states & InstanceStates.ContextType:
            self.is_context = True

        instance._publish_states = publish_states
        instance._logs = []
        instance.optional = getattr(instance, "optional", True)
        instance.data["publish"] = instance.data.get("publish", True)
        instance.data["label"] = (
            instance.data.get("label")
            or getattr(instance, "label", None)
            or instance.data["name"]
        )

        family = self.data(Roles.FamiliesRole)[0]
        self.setData(
            "{}.{}".format(family, self.instance.data["name"]),
            Roles.ObjectUIdRole
        )

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def type(self):
        return InstanceType

    def data(self, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if settings.UseLabel:
                return self.instance.data["label"]
            return self.instance.data["name"]

        if role == QtCore.Qt.DecorationRole:
            icon_name = self.instance.data.get("icon") or "file"
            return QAwesomeTextIconFactory.icon(icon_name)

        if role == Roles.TypeRole:
            return self.type()

        if role == Roles.ObjectIdRole:
            return self.instance.id

        if role == Roles.FamiliesRole:
            if self.is_context:
                return ["Context"]

            families = []
            family = self.instance.data.get("family")
            if family:
                families.append(family)

            _families = self.instance.data.get("families") or []
            for _family in _families:
                if _family not in families:
                    families.append(_family)

            return families

        if role == Roles.IsOptionalRole:
            return self.instance.optional

        if role == QtCore.Qt.CheckStateRole:
            return self.instance.data["publish"]

        if role == Roles.PublishFlagsRole:
            return self.instance._publish_states

        if role == Roles.LogRecordsRole:
            return self.instance._logs

        return super(InstanceItem, self).data(role)

    def setData(self, value, role=(QtCore.Qt.UserRole + 1)):
        if role == QtCore.Qt.CheckStateRole:
            if not self.data(Roles.IsEnabledRole):
                return
            self.instance.data["publish"] = value
            self.emitDataChanged()
            return

        if role == Roles.IsEnabledRole:
            if not self.instance.optional:
                return

        if role == Roles.PublishFlagsRole:
            if isinstance(value, list):
                _value = self.instance._publish_states
                for flag in value:
                    _value |= flag
                value = _value

            elif isinstance(value, dict):
                _value = self.instance._publish_states
                for flag, _bool in value.items():
                    if _bool is True:
                        _value |= flag
                    elif _value & flag:
                        _value ^= flag
                value = _value

            if value & InstanceStates.HasWarning:
                if self.parent():
                    self.parent().setData(
                        {GroupStates.HasWarning: True},
                        Roles.PublishFlagsRole
                    )
            if value & InstanceStates.HasError:
                if self.parent():
                    self.parent().setData(
                        {GroupStates.HasError: True},
                        Roles.PublishFlagsRole
                    )

            self.instance._publish_states = value
            self.emitDataChanged()
            return

        if role == Roles.LogRecordsRole:
            self.instance._logs = value
            self.emitDataChanged()
            return

        return super(InstanceItem, self).setData(value, role)


class InstanceModel(QtGui.QStandardItemModel):

    group_created = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, controller, *args, **kwargs):
        super(InstanceModel, self).__init__(*args, **kwargs)

        self.controller = controller
        self.checkstates = {}
        self.group_items = {}
        self.instance_items = {}

    def reset(self):
        self.group_items = {}
        self.instance_items = {}
        self.clear()

    def append(self, instance):
        new_item = InstanceItem(instance)
        if new_item.is_context:
            self.appendRow(new_item)
        else:
            families = new_item.data(Roles.FamiliesRole)
            group_item = self.group_items.get(families[0])
            if not group_item:
                group_item = GroupItem(families[0])
                self.appendRow(group_item)
                self.group_items[families[0]] = group_item
                self.group_created.emit(group_item.index())

            group_item.appendRow(new_item)
        instance_id = instance.id
        self.instance_items[instance_id] = new_item

    def remove(self, instance_id):
        instance_item = self.instance_items.pop(instance_id)
        parent_item = instance_item.parent()
        parent_item.removeRow(instance_item.row())
        if parent_item.rowCount():
            return

        self.group_items.pop(parent_item.data(QtCore.Qt.DisplayRole))
        self.removeRow(parent_item.row())

    def store_checkstates(self):
        self.checkstates.clear()

        for instance_item in self.instance_items.values():
            if not instance_item.instance.optional:
                continue

            uid = instance_item.data(Roles.ObjectUIdRole)
            self.checkstates[uid] = instance_item.data(
                QtCore.Qt.CheckStateRole
            )

    def restore_checkstates(self):
        for instance_item in self.instance_items.values():
            if not instance_item.instance.optional:
                continue

            uid = instance_item.data(Roles.ObjectUIdRole)
            state = self.checkstates.get(uid)
            if state is not None:
                instance_item.setData(state, QtCore.Qt.CheckStateRole)

    def update_with_result(self, result):
        instance = result["instance"]
        if instance is None:
            instance_id = self.controller.context.id
        else:
            instance_id = instance.id

        item = self.instance_items.get(instance_id)
        if not item:
            return

        new_flag_states = {
            InstanceStates.InProgress: False
        }

        publish_states = item.data(Roles.PublishFlagsRole)
        has_warning = publish_states & InstanceStates.HasWarning
        new_records = result.get("records") or []
        if not has_warning:
            for record in new_records:
                level_no = record.get("levelno")
                if level_no and level_no >= 30:
                    new_flag_states[InstanceStates.HasWarning] = True
                    break

        if (
            not publish_states & InstanceStates.HasError
            and not result["success"]
        ):
            new_flag_states[InstanceStates.HasError] = True

        item.setData(new_flag_states, Roles.PublishFlagsRole)

        records = item.data(Roles.LogRecordsRole) or []
        records.extend(new_records)

        item.setData(records, Roles.LogRecordsRole)

        return item

    def update_compatibility(self, context, instances):
        families = util.collect_families_from_instances(context, True)
        for plugin_item in self.plugin_items.values():
            publish_states = plugin_item.data(Roles.PublishFlagsRole)
            if (
                publish_states & PluginStates.WasProcessed
                or publish_states & PluginStates.WasSkipped
            ):
                continue

            is_compatible = False
            # A plugin should always show if it has processed.
            if plugin_item.plugin.__instanceEnabled__:
                compatibleInstances = pyblish.logic.instances_by_plugin(
                    context, plugin_item.plugin
                )
                for instance in instances:
                    if not instance.data.get("publish"):
                        continue

                    if instance in compatibleInstances:
                        is_compatible = True
                        break
            else:
                plugins = pyblish.logic.plugins_by_families(
                    [plugin_item.plugin], families
                )
                if plugins:
                    is_compatible = True

            current_is_compatible = publish_states & PluginStates.IsCompatible
            if (
                (is_compatible and not current_is_compatible)
                or (not is_compatible and current_is_compatible)
            ):
                plugin_item.setData(
                    {PluginStates.IsCompatible: is_compatible},
                    Roles.PublishFlagsRole
                )


class InstanceSortProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(InstanceSortProxy, self).__init__(*args, **kwargs)
        # Do not care about lower/upper case
        self.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

    def lessThan(self, x_index, y_index):
        x_type = x_index.data(Roles.TypeRole)
        y_type = y_index.data(Roles.TypeRole)
        if x_type != y_type:
            if x_type == GroupType:
                return False
            return True
        return super(InstanceSortProxy, self).lessThan(x_index, y_index)


class TerminalDetailItem(QtGui.QStandardItem):
    key_label_record_map = (
        ("instance", "Instance"),
        ("msg", "Message"),
        ("name", "Plugin"),
        ("pathname", "Path"),
        ("lineno", "Line"),
        ("traceback", "Traceback"),
        ("levelname", "Level"),
        ("threadName", "Thread"),
        ("msecs", "Millis")
    )

    def __init__(self, record_item):
        self.record_item = record_item
        self.msg = None
        msg = record_item.get("msg")
        if msg is None:
            msg = record_item["label"].split("\n")[0]

        super(TerminalDetailItem, self).__init__(msg)

    def data(self, role=QtCore.Qt.DisplayRole):
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if self.msg is None:
                self.msg = self.compute_detail_text(self.record_item)
            return self.msg
        return super(TerminalDetailItem, self).data(role)

    def compute_detail_text(self, item_data):
        if item_data["type"] == "info":
            return item_data["label"]

        html_text = ""
        for key, title in self.key_label_record_map:
            if key not in item_data:
                continue
            value = item_data[key]
            text = (
                str(value)
                .replace("<", "&#60;")
                .replace(">", "&#62;")
                .replace('\n', '<br/>')
                .replace(' ', '&nbsp;')
            )

            title_tag = (
                '<span style=\" font-size:8pt; font-weight:600;'
                # ' background-color:#bbb; color:#333;\" >{}:</span> '
                ' color:#fff;\" >{}:</span> '
            ).format(title)

            html_text += (
                '<tr><td width="100%" align=left>{}</td></tr>'
                '<tr><td width="100%">{}</td></tr>'
            ).format(title_tag, text)

        html_text = '<table width="100%" cellspacing="3">{}</table>'.format(
            html_text
        )
        return html_text


class TerminalModel(QtGui.QStandardItemModel):
    item_icon_name = {
        "info": "fa.info",
        "record": "fa.circle",
        "error": "fa.exclamation-triangle",
    }

    item_icon_colors = {
        "info": "#ffffff",
        "error": "#ff4a4a",
        "log_debug": "#ff66e8",
        "log_info": "#66abff",
        "log_warning": "#ffba66",
        "log_error": "#ff4d58",
        "log_critical": "#ff4f75",
        None: "#333333"
    }

    level_to_record = (
        (10, "log_debug"),
        (20, "log_info"),
        (30, "log_warning"),
        (40, "log_error"),
        (50, "log_critical")

    )

    def __init__(self, *args, **kwargs):
        super(TerminalModel, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.clear()

    def prepare_records(self, result, suspend_logs):
        prepared_records = []
        instance_name = None
        instance = result["instance"]
        if instance is not None:
            instance_name = instance.data["name"]

        if not suspend_logs:
            for record in result.get("records") or []:
                if isinstance(record, dict):
                    record_item = record
                else:
                    record_item = {
                        "label": text_type(record.msg),
                        "type": "record",
                        "levelno": record.levelno,
                        "threadName": record.threadName,
                        "name": record.name,
                        "filename": record.filename,
                        "pathname": record.pathname,
                        "lineno": record.lineno,
                        "msg": text_type(record.msg),
                        "msecs": record.msecs,
                        "levelname": record.levelname
                    }

                if instance_name is not None:
                    record_item["instance"] = instance_name

                prepared_records.append(record_item)

        error = result.get("error")
        if error:
            fname, line_no, func, exc = error.traceback
            error_item = {
                "label": str(error),
                "type": "error",
                "filename": str(fname),
                "lineno": str(line_no),
                "func": str(func),
                "traceback": error.formatted_traceback,
            }

            if instance_name is not None:
                error_item["instance"] = instance_name

            prepared_records.append(error_item)

        return prepared_records

    def append(self, record_items):
        all_record_items = []
        for record_item in record_items:
            record_type = record_item["type"]
            # Add error message to detail
            if record_type == "error":
                record_item["msg"] = record_item["label"]
            terminal_item_type = None
            if record_type == "record":
                for level, _type in self.level_to_record:
                    if level > record_item["levelno"]:
                        break
                    terminal_item_type = _type

            else:
                terminal_item_type = record_type

            icon_color = self.item_icon_colors.get(terminal_item_type)
            icon_name = self.item_icon_name.get(record_type)

            top_item_icon = None
            if icon_color and icon_name:
                top_item_icon = QAwesomeIconFactory.icon(icon_name, icon_color)

            label = record_item["label"].split("\n")[0]

            top_item = QtGui.QStandardItem()
            all_record_items.append(top_item)

            detail_item = TerminalDetailItem(record_item)
            top_item.appendRow(detail_item)

            top_item.setData(TerminalLabelType, Roles.TypeRole)
            top_item.setData(terminal_item_type, Roles.TerminalItemTypeRole)
            top_item.setData(label, QtCore.Qt.DisplayRole)
            top_item.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            )

            if top_item_icon:
                top_item.setData(top_item_icon, QtCore.Qt.DecorationRole)

            detail_item.setData(TerminalDetailType, Roles.TypeRole)

        self.invisibleRootItem().appendRows(all_record_items)

    def update_with_result(self, result):
        self.append(result["records"])


class TerminalProxy(QtCore.QSortFilterProxyModel):
    filter_buttons_checks = {
        "info": settings.TerminalFilters.get("info", True),
        "log_debug": settings.TerminalFilters.get("log_debug", True),
        "log_info": settings.TerminalFilters.get("log_info", True),
        "log_warning": settings.TerminalFilters.get("log_warning", True),
        "log_error": settings.TerminalFilters.get("log_error", True),
        "log_critical": settings.TerminalFilters.get("log_critical", True),
        "error": settings.TerminalFilters.get("error", True)
    }

    instances = []

    def __init__(self, view, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.__class__.instances.append(self)
        # Store parent because by own `QSortFilterProxyModel` has `parent`
        # method not returning parent QObject in PySide and PyQt4
        self.view = view

    @classmethod
    def change_filter(cls, name, value):
        cls.filter_buttons_checks[name] = value

        for instance in cls.instances:
            try:
                instance.invalidate()
                if instance.view:
                    instance.view.updateGeometry()

            except RuntimeError:
                # C++ Object was deleted
                cls.instances.remove(instance)

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        item_type = index.data(Roles.TypeRole)
        if not item_type == TerminalLabelType:
            return True
        terminal_item_type = index.data(Roles.TerminalItemTypeRole)
        return self.__class__.filter_buttons_checks.get(
            terminal_item_type, True
        )
