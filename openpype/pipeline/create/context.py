import copy
import logging
import collections
import inspect
from uuid import uuid4

from ..lib import UnknownDef
from .creator_plugins import BaseCreator

from openpype.api import (
    get_system_settings,
    get_project_settings
)


class InstanceMember:
    def __init__(self, instance, name):
        self.instance = instance

        instance.add_members(self)

        self.name = name
        self._actions = []

    def add_action(self, label, callback):
        self._actions.append({
            "label": label,
            "callback": callback
        })


class AttributeValues:
    def __init__(self, attr_defs, values, origin_data=None):
        if origin_data is None:
            origin_data = copy.deepcopy(values)
        self._origin_data = origin_data

        attr_defs_by_key = {
            attr_def.key: attr_def
            for attr_def in attr_defs
        }
        for key, value in values.items():
            if key not in attr_defs_by_key:
                new_def = UnknownDef(key, label=key, default=value)
                attr_defs.append(new_def)
                attr_defs_by_key[key] = new_def

        self._attr_defs = attr_defs
        self._attr_defs_by_key = attr_defs_by_key

        self._data = {}
        for attr_def in attr_defs:
            value = values.get(attr_def.key)
            if value is not None:
                self._data[attr_def.key] = value

    def __setitem__(self, key, value):
        if key not in self._attr_defs_by_key:
            raise KeyError("Key \"{}\" was not found.".format(key))

        old_value = self._data.get(key)
        if old_value == value:
            return
        self._data[key] = value

    def __getitem__(self, key):
        if key not in self._attr_defs_by_key:
            return self._data[key]
        return self._data.get(key, self._attr_defs_by_key[key].default)

    def __contains__(self, key):
        return key in self._attr_defs_by_key

    def get(self, key, default=None):
        if key in self._attr_defs_by_key:
            return self[key]
        return default

    def keys(self):
        return self._attr_defs_by_key.keys()

    def values(self):
        for key in self._attr_defs_by_key.keys():
            yield self._data.get(key)

    def items(self):
        for key in self._attr_defs_by_key.keys():
            yield key, self._data.get(key)

    def update(self, value):
        for _key, _value in dict(value):
            self[_key] = _value

    def pop(self, key, default=None):
        return self._data.pop(key, default)

    @property
    def attr_defs(self):
        return self._attr_defs

    def data_to_store(self):
        output = {}
        for key in self._data:
            output[key] = self[key]
        return output

    @staticmethod
    def calculate_changes(new_data, old_data):
        changes = {}
        for key, new_value in new_data.items():
            old_value = old_data.get(key)
            if old_value != new_value:
                changes[key] = (old_value, new_value)
        return changes

    def changes(self):
        return self.calculate_changes(self._data, self._origin_data)


class FamilyAttributeValues(AttributeValues):
    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        super(FamilyAttributeValues, self).__init__(*args, **kwargs)


class PublishAttributeValues(AttributeValues):
    def __init__(self, publish_attributes, *args, **kwargs):
        self.publish_attributes = publish_attributes
        super(PublishAttributeValues, self).__init__(*args, **kwargs)

    @property
    def instance(self):
        self.publish_attributes.instance


class PublishAttributes:
    def __init__(self, instance, origin_data, attr_plugins=None):
        self.instance = instance
        self._origin_data = copy.deepcopy(origin_data)

        attr_plugins = attr_plugins or []
        self.attr_plugins = attr_plugins

        self._data = {}
        self._plugin_names_order = []
        data = copy.deepcopy(origin_data)
        for plugin in attr_plugins:
            data = plugin.convert_attribute_values(data)
            attr_defs = plugin.get_attribute_defs()
            if not attr_defs:
                continue

            key = plugin.__name__
            self._plugin_names_order.append(key)

            value = data.get(key) or {}
            orig_value = copy.deepcopy(origin_data.get(key) or {})
            self._data[key] = PublishAttributeValues(
                self, attr_defs, value, orig_value
            )

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def pop(self, key, default=None):
        # TODO implement
        if key not in self._data:
            return default

        # if key not in self._plugin_keys:

    def plugin_names_order(self):
        for name in self._plugin_names_order:
            yield name

    def data_to_store(self):
        output = {}
        for key, attr_value in self._data.items():
            output[key] = attr_value.data_to_store()
        return output

    def changes(self):
        changes = {}
        for key, attr_val in self._data.items():
            attr_changes = attr_val.changes()
            if attr_changes:
                if key not in changes:
                    changes[key] = {}
                changes[key].update(attr_val)

        for key, value in self._origin_data.items():
            if key not in self._data:
                changes[key] = (value, None)
        return changes

    def set_publish_plugins(self, attr_plugins):
        # TODO implement
        self.attr_plugins = attr_plugins or []
        for plugin in attr_plugins:
            attr_defs = plugin.get_attribute_defs()
            if not attr_defs:
                continue


class CreatedInstance:
    """Instance entity with data that will be stored to workfile.

    I think `data` must be required argument containing all minimum information
    about instance like "asset" and "task" and all data used for filling subset
    name as creators may have custom data for subset name filling.

    Args:
        family(str): Name of family that will be created.
        subset_name(str): Name of subset that will be created.
        data(dict): Data used for filling subset name or override data from
            already existing instance.
    """
    def __init__(
        self, family, subset_name, data=None, creator=None, host=None,
        attr_plugins=None, new=True
    ):
        if not host:
            import avalon.api

            host = avalon.api.registered_host()
        self.host = host
        self.creator = creator

        # Family of instance
        self.family = family
        # Subset name
        self.subset_name = subset_name
        # Instance members may have actions on them
        self._members = []

        # Create a copy of passed data to avoid changing them on the fly
        data = copy.deepcopy(data or {})
        # Store original value of passed data
        self._orig_data = copy.deepcopy(data)

        # Pop family and subset to preved unexpected changes
        data.pop("family", None)
        data.pop("subset", None)

        # Pop dictionary values that will be converted to objects to be able
        #   catch changes
        orig_family_attributes = data.pop("family_attributes", None) or {}
        orig_publish_attributes = data.pop("publish_attributes", None) or {}

        self._data = collections.OrderedDict()
        self._data["id"] = "pyblish.avalon.instance"
        self._data["family"] = family
        self._data["subset"] = subset_name
        self._data["active"] = data.get("active", True)

        # QUESTION handle version of instance here or in creator?
        if new:
            self._data["version"] = 1
        else:
            self._data["version"] = data.get("version")

        # Stored family specific attribute values
        # {key: value}
        new_family_values = copy.deepcopy(orig_family_attributes)
        family_attr_defs = []
        if creator is not None:
            new_family_values = creator.convert_family_attribute_values(
                new_family_values
            )
            family_attr_defs = creator.get_attribute_defs()

        self._data["family_attributes"] = FamilyAttributeValues(
            self, family_attr_defs, new_family_values, orig_family_attributes
        )

        # Stored publish specific attribute values
        # {<plugin name>: {key: value}}
        self._data["publish_attributes"] = PublishAttributes(
            self, orig_publish_attributes, attr_plugins
        )
        if data:
            self._data.update(data)

        if not self._data.get("uuid"):
            self._data["uuid"] = str(uuid4())

    @property
    def id(self):
        return self._data["uuid"]

    @property
    def data(self):
        return self._data

    def changes(self):
        changes = {}
        new_keys = set()
        for key, new_value in self._data.items():
            new_keys.add(key)
            if key in ("family_attributes", "publish_attributes"):
                continue

            old_value = self._orig_data.get(key)
            if old_value != new_value:
                changes[key] = (old_value, new_value)

        family_attributes = self.data["family_attributes"]
        family_attr_changes = family_attributes.changes()
        if family_attr_changes:
            changes["family_attributes"] = family_attr_changes

        publish_attr_changes = self.publish_attributes.changes()
        if publish_attr_changes:
            changes["publish_attributes"] = publish_attr_changes

        for key, old_value in self._orig_data.items():
            if key not in new_keys:
                changes[key] = (old_value, None)
        return changes

    @property
    def family_attribute_defs(self):
        return self._data["family_attributes"].attr_defs

    @property
    def publish_attributes(self):
        return self._data["publish_attributes"]

    def data_to_store(self):
        output = collections.OrderedDict()
        for key, value in self._data.items():
            if key in ("family_attributes", "publish_attributes"):
                continue
            output[key] = value

        family_attributes = self._data["family_attributes"]
        output["family_attributes"] = family_attributes.data_to_store()

        publish_attributes = self._data["publish_attributes"]
        output["publish_attributes"] = publish_attributes.data_to_store()

        return output

    @classmethod
    def from_existing(
        cls, instance_data, creator=None, host=None, attr_plugins=None
    ):
        """Convert instance data from workfile to CreatedInstance."""
        instance_data = copy.deepcopy(instance_data)

        family = instance_data.get("family", None)
        subset_name = instance_data.get("subset", None)

        return cls(
            family, subset_name, instance_data, creator, host,
            attr_plugins, new=False
        )

    def set_publish_plugins(self, attr_plugins):
        self._data["publish_attributes"].set_publish_plugins(attr_plugins)

    def add_members(self, members):
        for member in members:
            if member not in self._members:
                self._members.append(member)


class CreateContext:
    def __init__(self, host, dbcon=None, headless=False, reset=True):
        if dbcon is None:
            import avalon.api

            session = avalon.api.session_data_from_environment(True)
            dbcon = avalon.api.AvalonMongoDB(session)
            dbcon.install()

        self.dbcon = dbcon

        self.host = host
        self.headless = headless

        self.instances = []

        self.creators = {}
        self.publish_plugins = []
        self.plugins_with_defs = []
        self._attr_plugins_by_family = {}

        self._log = None

        if reset:
            self.reset()

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    def reset(self):
        self.reset_plugins()
        self.reset_instances()

    def reset_plugins(self):
        import avalon.api
        import pyblish.api

        from openpype.pipeline import OpenPypePyblishPluginMixin

        # Reset publish plugins
        self._attr_plugins_by_family = {}

        publish_plugins = pyblish.api.discover()
        self.publish_plugins = publish_plugins

        # Collect plugins that can have attribute definitions
        plugins_with_defs = []
        for plugin in publish_plugins:
            if OpenPypePyblishPluginMixin in inspect.getmro(plugin):
                plugins_with_defs.append(plugin)
        self.plugins_with_defs = plugins_with_defs

        # Prepare settings
        project_name = self.dbcon.Session["AVALON_PROJECT"]
        system_settings = get_system_settings()
        project_settings = get_project_settings(project_name)

        # Discover and prepare creators
        creators = {}
        for creator in avalon.api.discover(BaseCreator):
            if inspect.isabstract(creator):
                self.log.info(
                    "Skipping abstract Creator {}".format(str(creator))
                )
                continue
            creators[creator.family] = creator(
                self,
                system_settings,
                project_settings,
                self.headless
            )

        self.creators = creators

    def reset_instances(self):
        # Collect instances
        host_instances = self.host.list_instances()
        instances = []
        for instance_data in host_instances:
            family = instance_data["family"]
            # Prepare publish plugins with attribute definitions
            creator = self.creators.get(family)
            attr_plugins = self._get_publish_plugins_with_attr_for_family(
                family
            )
            instance = CreatedInstance.from_existing(
                instance_data, creator, self.host, attr_plugins
            )
            instances.append(instance)

        self.instances = instances

    def _get_publish_plugins_with_attr_for_family(self, family):
        if family not in self._attr_plugins_by_family:
            import pyblish.logic

            filtered_plugins = pyblish.logic.plugins_by_families(
                self.plugins_with_defs, [family]
            )
            self._attr_plugins_by_family[family] = filtered_plugins

        return self._attr_plugins_by_family[family]
