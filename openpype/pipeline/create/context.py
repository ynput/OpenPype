import os
import copy
import logging
import collections
import inspect
from uuid import uuid4
from contextlib import contextmanager

from openpype.pipeline import legacy_io
from openpype.pipeline.mongodb import (
    AvalonMongoDB,
    session_data_from_environment,
)

from .creator_plugins import (
    Creator,
    AutoCreator,
    discover_creator_plugins,
)

from openpype.api import (
    get_system_settings,
    get_project_settings
)

UpdateData = collections.namedtuple("UpdateData", ["instance", "changes"])


class ImmutableKeyError(TypeError):
    """Accessed key is immutable so does not allow changes or removements."""
    def __init__(self, key, msg=None):
        self.immutable_key = key
        if not msg:
            msg = "Key \"{}\" is immutable and does not allow changes.".format(
                key
            )
        super(ImmutableKeyError, self).__init__(msg)


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
        from openpype.lib.attribute_definitions import UnknownDef

        if origin_data is None:
            origin_data = copy.deepcopy(values)
        self._origin_data = origin_data

        attr_defs_by_key = {
            attr_def.key: attr_def
            for attr_def in attr_defs
            if attr_def.is_value_def
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


class CreatorAttributeValues(AttributeValues):
    """Creator specific attribute values of an instance.

    Args:
        instance (CreatedInstance): Instance for which are values hold.
    """
    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        super(CreatorAttributeValues, self).__init__(*args, **kwargs)


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

        self._data = copy.deepcopy(origin_data)
        self._plugin_names_order = []
        self._missing_plugins = []

        self.set_publish_plugins(attr_plugins)

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
        """Plugin names order by their 'order' attribute."""
        for name in self._plugin_names_order:
            yield name

    def data_to_store(self):
        """Convert attribute values to "data to store"."""
        output = {}
        for key, attr_value in self._data.items():
            output[key] = attr_value.data_to_store()
        return output

    def changes(self):
        """Return changes per each key."""
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
        """Set publish plugins attribute definitions."""
        self._plugin_names_order = []
        self._missing_plugins = []
        self.attr_plugins = attr_plugins or []

        origin_data = self._origin_data
        data = self._data
        self._data = {}
        added_keys = set()
        for plugin in attr_plugins:
            output = plugin.convert_attribute_values(data)
            if output is not None:
                data = output
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
        creator(BaseCreator): Creator responsible for instance.
        host(ModuleType): Host implementation loaded with
            `openpype.pipeline.registered_host`.
        new(bool): Is instance new.
    """
    # Keys that can't be changed or removed from data after loading using
    #   creator.
    # - 'creator_attributes' and 'publish_attributes' can change values of
    #   their individual children but not on their own
    __immutable_keys = (
        "id",
        "instance_id",
        "family",
        "creator_identifier",
        "creator_attributes",
        "publish_attributes"
    )

    def __init__(
        self, family, subset_name, data, creator, new=True
    ):
        self.creator = creator

        # Instance members may have actions on them
        self._members = []

        # Create a copy of passed data to avoid changing them on the fly
        data = copy.deepcopy(data or {})
        # Store original value of passed data
        self._orig_data = copy.deepcopy(data)

        # Pop family and subset to prevent unexpected changes
        data.pop("family", None)
        data.pop("subset", None)

        # Pop dictionary values that will be converted to objects to be able
        #   catch changes
        orig_creator_attributes = data.pop("creator_attributes", None) or {}
        orig_publish_attributes = data.pop("publish_attributes", None) or {}

        # QUESTION Does it make sense to have data stored as ordered dict?
        self._data = collections.OrderedDict()
        # QUESTION Do we need this "id" information on instance?
        self._data["id"] = "pyblish.avalon.instance"
        self._data["family"] = family
        self._data["subset"] = subset_name
        self._data["active"] = data.get("active", True)
        self._data["creator_identifier"] = creator.identifier

        # Pop from source data all keys that are defined in `_data` before
        #   this moment and through their values away
        # - they should be the same and if are not then should not change
        #   already set values
        for key in self._data.keys():
            if key in data:
                data.pop(key)

        # Stored creator specific attribute values
        # {key: value}
        creator_values = copy.deepcopy(orig_creator_attributes)
        creator_attr_defs = creator.get_instance_attr_defs()

        self._data["creator_attributes"] = CreatorAttributeValues(
            self, creator_attr_defs, creator_values, orig_creator_attributes
        )

        # Stored publish specific attribute values
        # {<plugin name>: {key: value}}
        # - must be set using 'set_publish_plugins'
        self._data["publish_attributes"] = PublishAttributes(
            self, orig_publish_attributes, None
        )
        if data:
            self._data.update(data)

        if not self._data.get("instance_id"):
            self._data["instance_id"] = str(uuid4())

        self._asset_is_valid = self.has_set_asset
        self._task_is_valid = self.has_set_task

    def __str__(self):
        return (
            "<CreatedInstance {subset} ({family}[{creator_identifier}])>"
            " {data}"
        ).format(
            subset=str(self._data),
            creator_identifier=self.creator_identifier,
            family=self.family,
            data=str(self._data)
        )

    # --- Dictionary like methods ---
    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __setitem__(self, key, value):
        # Validate immutable keys
        if key not in self.__immutable_keys:
            self._data[key] = value

        elif value != self._data.get(key):
            # Raise exception if key is immutable and value has changed
            raise ImmutableKeyError(key)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, *args, **kwargs):
        # Raise exception if is trying to pop key which is immutable
        if key in self.__immutable_keys:
            raise ImmutableKeyError(key)

        self._data.pop(key, *args, **kwargs)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()
    # ------

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
    def creator_label(self):
        return self.creator.label or self.creator_identifier

    @property
    def create_context(self):
        return self.creator.create_context

    @property
    def host(self):
        return self.create_context.host

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
        return self._data["instance_id"]

    @property
    def data(self):
        """Legacy access to data.

        Access to data is needed to modify values.
        """
        return self

    def changes(self):
        """Calculate and return changes."""
        changes = {}
        new_keys = set()
        for key, new_value in self._data.items():
            new_keys.add(key)
            if key in ("creator_attributes", "publish_attributes"):
                continue

            old_value = self._orig_data.get(key)
            if old_value != new_value:
                changes[key] = (old_value, new_value)

        creator_attr_changes = self.creator_attributes.changes()
        if creator_attr_changes:
            changes["creator_attributes"] = creator_attr_changes

        publish_attr_changes = self.publish_attributes.changes()
        if publish_attr_changes:
            changes["publish_attributes"] = publish_attr_changes

        for key, old_value in self._orig_data.items():
            if key not in new_keys:
                changes[key] = (old_value, None)
        return changes

    @property
    def creator_attributes(self):
        return self._data["creator_attributes"]

    @property
    def creator_attribute_defs(self):
        return self.creator_attributes.attr_defs

    @property
    def publish_attributes(self):
        return self._data["publish_attributes"]

    def data_to_store(self):
        output = collections.OrderedDict()
        for key, value in self._data.items():
            if key in ("creator_attributes", "publish_attributes"):
                continue
            output[key] = value

        output["creator_attributes"] = self.creator_attributes.data_to_store()
        output["publish_attributes"] = self.publish_attributes.data_to_store()

        return output

    @classmethod
    def from_existing(cls, instance_data, creator):
        """Convert instance data from workfile to CreatedInstance."""
        instance_data = copy.deepcopy(instance_data)

        family = instance_data.get("family", None)
        if family is None:
            family = creator.family
        subset_name = instance_data.get("subset", None)

        return cls(
            family, subset_name, instance_data, creator, new=False
        )

    def set_publish_plugins(self, attr_plugins):
        self.publish_attributes.set_publish_plugins(attr_plugins)

    def add_members(self, members):
        """Currently unused method."""
        for member in members:
            if member not in self._members:
                self._members.append(member)


class CreateContext:
    """Context of instance creation.

    Context itself also can store data related to whole creation (workfile).
    - those are mainly for Context publish plugins

    Args:
        host(ModuleType): Host implementation which handles implementation and
            global metadata.
        dbcon(AvalonMongoDB): Connection to mongo with context (at least
            project).
        headless(bool): Context is created out of UI (Current not used).
        reset(bool): Reset context on initialization.
        discover_publish_plugins(bool): Discover publish plugins during reset
            phase.
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
        # Create conncetion if is not passed
        if dbcon is None:
            session = session_data_from_environment(True)
            dbcon = AvalonMongoDB(session)
            dbcon.install()

        self.dbcon = dbcon
        self.host = host

        # Prepare attribute for logger (Created on demand in `log` property)
        self._log = None

        # Publish context plugins attributes and it's values
        self._publish_attributes = PublishAttributes(self, {})
        self._original_context_data = {}

        # Validate host implementation
        # - defines if context is capable of handling context data
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
        # Currently unused variable
        self.headless = headless

        # Instances by their ID
        self._instances_by_id = {}

        # Discovered creators
        self.creators = {}
        # Prepare categories of creators
        self.autocreators = {}
        # Manual creators
        self.manual_creators = {}

        self.publish_discover_result = None
        self.publish_plugins = []
        self.plugins_with_defs = []
        self._attr_plugins_by_family = {}

        # Helpers for validating context of collected instances
        #   - they can be validation for multiple instances at one time
        #       using context manager which will trigger validation
        #       after leaving of last context manager scope
        self._bulk_counter = 0
        self._bulk_instances_to_process = []

        # Trigger reset if was enabled
        if reset:
            self.reset(discover_publish_plugins)

    @property
    def instances(self):
        return self._instances_by_id.values()

    @property
    def publish_attributes(self):
        """Access to global publish attributes."""
        return self._publish_attributes

    @classmethod
    def get_host_misssing_methods(cls, host):
        """Collect missing methods from host.

        Args:
            host(ModuleType): Host implementaion.
        """
        missing = set()
        for attr_name in cls.required_methods:
            if not hasattr(host, attr_name):
                missing.add(attr_name)
        return missing

    @property
    def host_is_valid(self):
        """Is host valid for creation."""
        return self._host_is_valid

    @property
    def host_name(self):
        return os.environ["AVALON_APP"]

    @property
    def log(self):
        """Dynamic access to logger."""
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    def reset(self, discover_publish_plugins=True):
        """Reset context with all plugins and instances.

        All changes will be lost if were not saved explicitely.
        """
        self.reset_avalon_context()
        self.reset_plugins(discover_publish_plugins)
        self.reset_context_data()

        with self.bulk_instances_collection():
            self.reset_instances()
            self.execute_autocreators()

    def reset_avalon_context(self):
        """Give ability to reset avalon context.

        Reset is based on optional host implementation of `get_current_context`
        function or using `legacy_io.Session`.

        Some hosts have ability to change context file without using workfiles
        tool but that change is not propagated to
        """

        project_name = asset_name = task_name = None
        if hasattr(self.host, "get_current_context"):
            host_context = self.host.get_current_context()
            if host_context:
                project_name = host_context.get("project_name")
                asset_name = host_context.get("asset_name")
                task_name = host_context.get("task_name")

        if not project_name:
            project_name = legacy_io.Session.get("AVALON_PROJECT")
        if not asset_name:
            asset_name = legacy_io.Session.get("AVALON_ASSET")
        if not task_name:
            task_name = legacy_io.Session.get("AVALON_TASK")

        if project_name:
            self.dbcon.Session["AVALON_PROJECT"] = project_name
        if asset_name:
            self.dbcon.Session["AVALON_ASSET"] = asset_name
        if task_name:
            self.dbcon.Session["AVALON_TASK"] = task_name

    def reset_plugins(self, discover_publish_plugins=True):
        """Reload plugins.

        Reloads creators from preregistered paths and can load publish plugins
        if it's enabled on context.
        """
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
        manual_creators = {}
        for creator_class in discover_creator_plugins():
            if inspect.isabstract(creator_class):
                self.log.info(
                    "Skipping abstract Creator {}".format(str(creator_class))
                )
                continue

            creator_identifier = creator_class.identifier
            if creator_identifier in creators:
                self.log.warning((
                    "Duplicated Creator identifier. "
                    "Using first and skipping following"
                ))
                continue

            # Filter by host name
            if (
                creator_class.host_name
                and creator_class.host_name != self.host_name
            ):
                self.log.info((
                    "Creator's host name is not supported for current host {}"
                ).format(creator_class.host_name, self.host_name))
                continue

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
                manual_creators[creator_identifier] = creator

        self.autocreators = autocreators
        self.manual_creators = manual_creators

        self.creators = creators

    def reset_context_data(self):
        """Reload context data using host implementation.

        These data are not related to any instance but may be needed for whole
        publishing.
        """
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
        """Data that should be stored by host function.

        The same data should be returned on loading.
        """
        return {
            "publish_attributes": self._publish_attributes.data_to_store()
        }

    def context_data_changes(self):
        """Changes of attributes."""
        changes = {}
        publish_attribute_changes = self._publish_attributes.changes()
        if publish_attribute_changes:
            changes["publish_attributes"] = publish_attribute_changes
        return changes

    def creator_adds_instance(self, instance):
        """Creator adds new instance to context.

        Instances should be added only from creators.

        Args:
            instance(CreatedInstance): Instance with prepared data from
                creator.

        TODO: Rename method to more suit.
        """
        # Add instance to instances list
        if instance.id in self._instances_by_id:
            self.log.warning((
                "Instance with id {} is already added to context."
            ).format(instance.id))
            return

        self._instances_by_id[instance.id] = instance
        # Prepare publish plugin attributes and set it on instance
        attr_plugins = self._get_publish_plugins_with_attr_for_family(
            instance.creator.family
        )
        instance.set_publish_plugins(attr_plugins)

        # Add instance to be validated inside 'bulk_instances_collection'
        #   context manager if is inside bulk
        with self.bulk_instances_collection():
            self._bulk_instances_to_process.append(instance)

    def creator_removed_instance(self, instance):
        self._instances_by_id.pop(instance.id, None)

    @contextmanager
    def bulk_instances_collection(self):
        """Validate context of instances in bulk.

        This can be used for single instance or for adding multiple instances
            which is helpfull on reset.

        Should not be executed from multiple threads.
        """
        self._bulk_counter += 1
        try:
            yield
        finally:
            self._bulk_counter -= 1

        # Trigger validation if there is no more context manager for bulk
        #   instance validation
        if self._bulk_counter == 0:
            (
                self._bulk_instances_to_process,
                instances_to_validate
            ) = (
                [],
                self._bulk_instances_to_process
            )
            self.validate_instances_context(instances_to_validate)

    def reset_instances(self):
        """Reload instances"""
        self._instances_by_id = {}

        # Collect instances
        for creator in self.creators.values():
            creator.collect_instances()

    def execute_autocreators(self):
        """Execute discovered AutoCreator plugins.

        Reset instances if any autocreator executed properly.
        """
        for identifier, creator in self.autocreators.items():
            try:
                creator.create()

            except Exception:
                # TODO raise report exception if any crashed
                msg = (
                    "Failed to run AutoCreator with identifier \"{}\" ({})."
                ).format(identifier, inspect.getfile(creator.__class__))
                self.log.warning(msg, exc_info=True)

    def validate_instances_context(self, instances=None):
        """Validate 'asset' and 'task' instance context."""
        # Use all instances from context if 'instances' are not passed
        if instances is None:
            instances = tuple(self._instances_by_id.values())

        # Skip if instances are empty
        if not instances:
            return

        task_names_by_asset_name = {}
        for instance in instances:
            task_name = instance.get("task")
            asset_name = instance.get("asset")
            if asset_name:
                task_names_by_asset_name[asset_name] = set()
                if task_name:
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

            asset_name = instance["asset"]
            if asset_name not in task_names_by_asset_name:
                instance.set_asset_invalid(True)
                continue

            task_name = instance["task"]
            if not task_name:
                continue

            if task_name not in task_names_by_asset_name[asset_name]:
                instance.set_task_invalid(True)

    def save_changes(self):
        """Save changes. Update all changed values."""
        if not self.host_is_valid:
            missing_methods = self.get_host_misssing_methods(self.host)
            raise HostMissRequiredMethod(self.host, missing_methods)

        self._save_context_changes()
        self._save_instance_changes()

    def _save_context_changes(self):
        """Save global context values."""
        changes = self.context_data_changes()
        if changes:
            data = self.context_data_to_store()
            self.host.update_context_data(data, changes)

    def _save_instance_changes(self):
        """Save instance specific values."""
        instances_by_identifier = collections.defaultdict(list)
        for instance in self._instances_by_id.values():
            identifier = instance.creator_identifier
            instances_by_identifier[identifier].append(instance)

        for identifier, cretor_instances in instances_by_identifier.items():
            update_list = []
            for instance in cretor_instances:
                instance_changes = instance.changes()
                if instance_changes:
                    update_list.append(UpdateData(instance, instance_changes))

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

        for identifier, creator_instances in instances_by_identifier.items():
            creator = self.creators.get(identifier)
            creator.remove_instances(creator_instances)

    def _get_publish_plugins_with_attr_for_family(self, family):
        """Publish plugin attributes for passed family.

        Attribute definitions for specific family are cached.

        Args:
            family(str): Instance family for which should be attribute
                definitions returned.
        """
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
        """Publish plugins attributes for Context plugins."""
        plugins = []
        for plugin in self.plugins_with_defs:
            if not plugin.__instanceEnabled__:
                plugins.append(plugin)
        return plugins
