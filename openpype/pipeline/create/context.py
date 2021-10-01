import os
import copy
import logging
import collections
import inspect
from uuid import uuid4

from ..lib import UnknownDef
from .creator_plugins import (
    BaseCreator,
    Creator,
    AutoCreator
)

from openpype.api import (
    get_system_settings,
    get_project_settings
)


class HostMissRequiredMethod(Exception):
    """Host does not have implemented required functions for creation."""
    def __init__(self, host, missing_methods):
        self.missing_methods = missing_methods
        self.host = host
        joined_methods = ", ".join(
            ['"{}"'.format(name) for name in missing_methods]
        )
        dirpath = os.path.dirname(
            os.path.normpath(inspect.getsourcefile(host))
        )
        dirpath_parts = dirpath.split(os.path.sep)
        host_name = dirpath_parts.pop(-1)
        if host_name == "api":
            host_name = dirpath_parts.pop(-1)

        msg = "Host \"{}\" does not have implemented method/s {}".format(
            host_name, joined_methods
        )
        super(HostMissRequiredMethod, self).__init__(msg)


class InstanceMember:
    """Representation of instance member.

    TODO:
    Implement and use!
    """
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
    """Container which keep values of Attribute definitions.

    Goal is to have one object which hold values of attribute definitions for
    single instance.

    Has dictionary like methods. Not all of them are allowed all the time.

    Args:
        attr_defs(AbtractAttrDef): Defintions of value type and properties.
        values(dict): Values after possible conversion.
        origin_data(dict): Values loaded from host before conversion.
    """
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

    def reset_values(self):
        self._data = []

    @property
    def attr_defs(self):
        """Pointer to attribute definitions."""
        return self._attr_defs

    def data_to_store(self):
        """Create new dictionary with data to store."""
        output = {}
        for key in self._data:
            output[key] = self[key]
        return output

    @staticmethod
    def calculate_changes(new_data, old_data):
        """Calculate changes of 2 dictionary objects."""
        changes = {}
        for key, new_value in new_data.items():
            old_value = old_data.get(key)
            if old_value != new_value:
                changes[key] = (old_value, new_value)
        return changes

    def changes(self):
        return self.calculate_changes(self._data, self._origin_data)


class FamilyAttributeValues(AttributeValues):
    """Family specific attribute values of an instance.

    Args:
        instance (CreatedInstance): Instance for which are values hold.
    """
    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        super(FamilyAttributeValues, self).__init__(*args, **kwargs)


class PublishAttributeValues(AttributeValues):
    """Publish plugin specific attribute values.

    Values are for single plugin which can be on `CreatedInstance`
    or context values stored on `CreateContext`.

    Args:
        publish_attributes(PublishAttributes): Wrapper for multiple publish
            attributes is used as parent object.
    """
    def __init__(self, publish_attributes, *args, **kwargs):
        self.publish_attributes = publish_attributes
        super(PublishAttributeValues, self).__init__(*args, **kwargs)

    @property
    def parent(self):
        self.publish_attributes.parent


class PublishAttributes:
    """Wrapper for publish plugin attribute definitions.

    Cares about handling attribute definitions of multiple publish plugins.

    Args:
        parent(CreatedInstance, CreateContext): Parent for which will be
            data stored and from which are data loaded.
        origin_data(dict): Loaded data by plugin class name.
        attr_plugins(list): List of publish plugins that may have defined
            attribute definitions.
    """
    def __init__(self, parent, origin_data, attr_plugins=None):
        self.parent = parent
        self._origin_data = copy.deepcopy(origin_data)

        attr_plugins = attr_plugins or []
        self.attr_plugins = attr_plugins

        self._data = {}
        self._plugin_names_order = []
        self._missing_plugins = []
        data = copy.deepcopy(origin_data)
        added_keys = set()
        for plugin in attr_plugins:
            data = plugin.convert_attribute_values(data)
            attr_defs = plugin.get_attribute_defs()
            if not attr_defs:
                continue

            key = plugin.__name__
            added_keys.add(key)
            self._plugin_names_order.append(key)

            value = data.get(key) or {}
            orig_value = copy.deepcopy(origin_data.get(key) or {})
            self._data[key] = PublishAttributeValues(
                self, attr_defs, value, orig_value
            )

        for key, value in data.items():
            if key not in added_keys:
                self._missing_plugins.append(key)
                self._data[key] = PublishAttributeValues(
                    self, [], value, value
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
        """Remove or reset value for plugin.

        Plugin values are reset to defaults if plugin is available but
        data of plugin which was not found are removed.

        Args:
            key(str): Plugin name.
            default: Default value if plugin was not found.
        """
        if key not in self._data:
            return default

        if key in self._missing_plugins:
            self._missing_plugins.remove(key)
            removed_item = self._data.pop(key)
            return removed_item.data_to_store()

        value_item = self._data[key]
        # Prepare value to return
        output = value_item.data_to_store()
        # Reset values
        value_item.reset_values()
        return output

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
        self, family, subset_name, data, creator, host=None,
        attr_plugins=None, new=True
    ):
        if host is None:
            import avalon.api

            host = avalon.api.registered_host()
        self.host = host
        self.creator = creator

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

        # QUESTION Does it make sense to have data stored as ordered dict?
        self._data = collections.OrderedDict()
        self._data["id"] = "pyblish.avalon.instance"
        self._data["family"] = family
        self._data["subset"] = subset_name
        self._data["active"] = data.get("active", True)
        self._data["creator_identifier"] = creator.identifier

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

        self._asset_is_valid = self.has_set_asset
        self._task_is_valid = self.has_set_task

    @property
    def family(self):
        return self._data["family"]

    @property
    def subset_name(self):
        return self._data["subset"]

    @property
    def creator_identifier(self):
        return self.creator.identifier

    @property
    def has_set_asset(self):
        """Asset name is set in data."""
        return "asset" in self._data

    @property
    def has_set_task(self):
        """Task name is set in data."""
        return "task" in self._data

    @property
    def has_valid_context(self):
        """Context data are valid for publishing."""
        return self.has_valid_asset and self.has_valid_task

    @property
    def has_valid_asset(self):
        """Asset set in context exists in project."""
        if not self.has_set_asset:
            return False
        return self._asset_is_valid

    @property
    def has_valid_task(self):
        """Task set in context exists in project."""
        if not self.has_set_task:
            return False
        return self._task_is_valid

    def set_asset_invalid(self, invalid):
        # TODO replace with `set_asset_name`
        self._asset_is_valid = not invalid

    def set_task_invalid(self, invalid):
        # TODO replace with `set_task_name`
        self._task_is_valid = not invalid

    @property
    def id(self):
        """Instance identifier."""
        return self._data["uuid"]

    @property
    def data(self):
        """Pointer to data.

        TODO:
        Define class handling which keys are change to what.
        - this is dangerous as it is possible to modify any key (e.g. `uuid`)
        """
        return self._data

    def changes(self):
        """Calculate and return changes."""
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
        cls, instance_data, creator, attr_plugins=None, host=None
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
    """Context of instance creation.

    Context itself also can store data related to whole creation (workfile).
    - those are mainly for Context publish plugins
    """
    # Methods required in host implementaion to be able create instances
    #   or change context data.
    required_methods = (
        "get_context_data",
        "update_context_data"
    )

    def __init__(
        self, host, dbcon=None, headless=False, reset=True,
        discover_publish_plugins=True
    ):
        if dbcon is None:
            import avalon.api

            session = avalon.api.session_data_from_environment(True)
            dbcon = avalon.api.AvalonMongoDB(session)
            dbcon.install()

        self.dbcon = dbcon

        self._log = None
        self._publish_attributes = PublishAttributes(self, {})
        self._original_context_data = {}

        self.host = host
        host_is_valid = True
        missing_methods = self.get_host_misssing_methods(host)
        if missing_methods:
            host_is_valid = False
            joined_methods = ", ".join(
                ['"{}"'.format(name) for name in missing_methods]
            )
            self.log.warning((
                "Host miss required methods to be able use creation."
                " Missing methods: {}"
            ).format(joined_methods))

        self._host_is_valid = host_is_valid
        self.headless = headless

        # TODO convert to dictionary instance by id to validate duplicates
        self.instances = []

        # Discovered creators
        self.creators = {}
        # Prepare categories of creators
        self.autocreators = {}
        self.ui_creators = {}

        self.publish_discover_result = None
        self.publish_plugins = []
        self.plugins_with_defs = []
        self._attr_plugins_by_family = {}

        self._reseting = False

        if reset:
            self.reset(discover_publish_plugins)

    @property
    def publish_attributes(self):
        return self._publish_attributes

    @classmethod
    def get_host_misssing_methods(cls, host):
        missing = set()
        for attr_name in cls.required_methods:
            if not hasattr(host, attr_name):
                missing.add(attr_name)
        return missing

    @property
    def host_is_valid(self):
        return self._host_is_valid

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    def reset(self, discover_publish_plugins=True):
        self._reseting = True

        self.reset_plugins(discover_publish_plugins)
        self.reset_context_data()
        self.reset_instances()
        self.execute_autocreators()

        self._validate_instances_context(self.instances)

        self._reseting = False

    def reset_plugins(self, discover_publish_plugins=True):
        import avalon.api
        import pyblish.logic

        from openpype.pipeline import OpenPypePyblishPluginMixin
        from openpype.pipeline.publish import (
            publish_plugins_discover,
            DiscoverResult
        )

        # Reset publish plugins
        self._attr_plugins_by_family = {}

        discover_result = DiscoverResult()
        plugins_with_defs = []
        plugins_by_targets = []
        if discover_publish_plugins:
            discover_result = publish_plugins_discover()
            publish_plugins = discover_result.plugins

            targets = pyblish.logic.registered_targets() or ["default"]
            plugins_by_targets = pyblish.logic.plugins_by_targets(
                publish_plugins, targets
            )
            # Collect plugins that can have attribute definitions
            for plugin in publish_plugins:
                if OpenPypePyblishPluginMixin in inspect.getmro(plugin):
                    plugins_with_defs.append(plugin)

        self.publish_discover_result = discover_result
        self.publish_plugins = plugins_by_targets
        self.plugins_with_defs = plugins_with_defs

        # Prepare settings
        project_name = self.dbcon.Session["AVALON_PROJECT"]
        system_settings = get_system_settings()
        project_settings = get_project_settings(project_name)

        # Discover and prepare creators
        creators = {}
        autocreators = {}
        ui_creators = {}
        for creator_class in avalon.api.discover(BaseCreator):
            if inspect.isabstract(creator_class):
                self.log.info(
                    "Skipping abstract Creator {}".format(str(creator_class))
                )
                continue

            creator_identifier = creator_class.identifier
            creator = creator_class(
                self,
                system_settings,
                project_settings,
                self.headless
            )
            creators[creator_identifier] = creator
            if isinstance(creator, AutoCreator):
                autocreators[creator_identifier] = creator
            elif isinstance(creator, Creator):
                ui_creators[creator_identifier] = creator

        self.autocreators = autocreators
        self.ui_creators = ui_creators

        self.creators = creators

    def reset_context_data(self):
        if not self.host_is_valid:
            self._original_context_data = {}
            self._publish_attributes = PublishAttributes(self, {})
            return

        original_data = self.host.get_context_data() or {}
        self._original_context_data = copy.deepcopy(original_data)

        publish_attributes = original_data.get("publish_attributes") or {}

        attr_plugins = self._get_publish_plugins_with_attr_for_context()
        self._publish_attributes = PublishAttributes(
            self, publish_attributes, attr_plugins
        )

    def context_data_to_store(self):
        return {
            "publish_attributes": self._publish_attributes.data_to_store()
        }

    def context_data_changes(self):
        changes = {}
        publish_attribute_changes = self._publish_attributes.changes()
        if publish_attribute_changes:
            changes["publish_attributes"] = publish_attribute_changes
        return changes

    def add_instance(self, instance):
        self.instances.append(instance)
        if not self._reseting:
            self._validate_instances_context([instance])

    def reset_instances(self):
        self.instances = []

        # Collect instances
        for creator in self.creators.values():
            family = creator.family
            attr_plugins = self._get_publish_plugins_with_attr_for_family(
                family
            )
            creator.collect_instances(attr_plugins)

    def execute_autocreators(self):
        """Execute discovered AutoCreator plugins.

        Reset instances if any autocreator executed properly.
        """
        for family, creator in self.autocreators.items():
            try:
                creator.create()

            except Exception:
                # TODO raise report exception if any crashed
                msg = (
                    "Failed to run AutoCreator with family \"{}\" ({})."
                ).format(family, inspect.getfile(creator.__class__))
                self.log.warning(msg, exc_info=True)

    def _validate_instances_context(self, instances):
        task_names_by_asset_name = collections.defaultdict(set)
        for instance in instances:
            task_name = instance.data.get("task")
            asset_name = instance.data.get("asset")
            if asset_name and task_name:
                task_names_by_asset_name[asset_name].add(task_name)

        asset_names = [
            asset_name
            for asset_name in task_names_by_asset_name.keys()
            if asset_name is not None
        ]
        asset_docs = list(self.dbcon.find(
            {
                "type": "asset",
                "name": {"$in": asset_names}
            },
            {
                "name": True,
                "data.tasks": True
            }
        ))

        task_names_by_asset_name = {}
        for asset_doc in asset_docs:
            asset_name = asset_doc["name"]
            tasks = asset_doc.get("data", {}).get("tasks") or {}
            task_names_by_asset_name[asset_name] = set(tasks.keys())

        for instance in instances:
            if not instance.has_valid_asset or not instance.has_valid_task:
                continue

            asset_name = instance.data["asset"]
            if asset_name not in task_names_by_asset_name:
                instance.set_asset_invalid(True)
                continue

            task_name = instance.data["task"]
            if not task_name:
                continue

            if task_name not in task_names_by_asset_name[asset_name]:
                instance.set_task_invalid(True)

    def save_changes(self):
        if not self.host_is_valid:
            missing_methods = self.get_host_misssing_methods(self.host)
            raise HostMissRequiredMethod(self.host, missing_methods)

        self._save_context_changes()
        self._save_instance_changes()

    def _save_context_changes(self):
        changes = self.context_data_changes()
        if changes:
            data = self.context_data_to_store()
            self.host.update_context_data(data, changes)

    def _save_instance_changes(self):
        instances_by_identifier = collections.defaultdict(list)
        for instance in self.instances:
            identifier = instance.creator_identifier
            instances_by_identifier[identifier].append(instance)

        for identifier, cretor_instances in instances_by_identifier.items():
            update_list = []
            for instance in cretor_instances:
                instance_changes = instance.changes()
                if instance_changes:
                    update_list.append((instance, instance_changes))

            creator = self.creators[identifier]
            if update_list:
                creator.update_instances(update_list)

    def remove_instances(self, instances):
        """Remove instances from context.

        Args:
            instances(list<CreatedInstance>): Instances that should be removed
                from context.
        """
        instances_by_identifier = collections.defaultdict(list)
        for instance in instances:
            identifier = instance.creator_identifier
            instances_by_identifier[identifier].append(instance)

        instances_to_remove = []
        for identifier, creator_instances in instances_by_identifier.items():
            creator = self.creators.get(identifier)
            creator.remove_instances(creator_instances)
            instances_to_remove.append(instances_to_remove)

    def _get_publish_plugins_with_attr_for_family(self, family):
        if family not in self._attr_plugins_by_family:
            import pyblish.logic

            filtered_plugins = pyblish.logic.plugins_by_families(
                self.plugins_with_defs, [family]
            )
            plugins = []
            for plugin in filtered_plugins:
                if plugin.__instanceEnabled__:
                    plugins.append(plugin)
            self._attr_plugins_by_family[family] = plugins

        return self._attr_plugins_by_family[family]

    def _get_publish_plugins_with_attr_for_context(self):
        plugins = []
        for plugin in self.plugins_with_defs:
            if not plugin.__instanceEnabled__:
                plugins.append(plugin)
        return plugins
