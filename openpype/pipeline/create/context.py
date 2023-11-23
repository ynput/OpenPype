import os
import sys
import copy
import logging
import traceback
import collections
import inspect
from uuid import uuid4
from contextlib import contextmanager

import pyblish.logic
import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.client import (
    get_assets,
    get_asset_by_name,
    get_asset_name_identifier,
)
from openpype.settings import (
    get_system_settings,
    get_project_settings
)
from openpype.lib.attribute_definitions import (
    UnknownDef,
    serialize_attr_defs,
    deserialize_attr_defs,
    get_default_values,
)
from openpype.host import IPublishHost, IWorkfileHost
from openpype.pipeline import legacy_io, Anatomy
from openpype.pipeline.plugin_discover import DiscoverResult

from .creator_plugins import (
    Creator,
    AutoCreator,
    discover_creator_plugins,
    discover_convertor_plugins,
    CreatorError,
)

# Changes of instances and context are send as tuple of 2 information
UpdateData = collections.namedtuple("UpdateData", ["instance", "changes"])


class UnavailableSharedData(Exception):
    """Shared data are not available at the moment when are accessed."""
    pass


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


class ConvertorsOperationFailed(Exception):
    def __init__(self, msg, failed_info):
        super(ConvertorsOperationFailed, self).__init__(msg)
        self.failed_info = failed_info


class ConvertorsFindFailed(ConvertorsOperationFailed):
    def __init__(self, failed_info):
        msg = "Failed to find incompatible subsets"
        super(ConvertorsFindFailed, self).__init__(
            msg, failed_info
        )


class ConvertorsConversionFailed(ConvertorsOperationFailed):
    def __init__(self, failed_info):
        msg = "Failed to convert incompatible subsets"
        super(ConvertorsConversionFailed, self).__init__(
            msg, failed_info
        )


def prepare_failed_convertor_operation_info(identifier, exc_info):
    exc_type, exc_value, exc_traceback = exc_info
    formatted_traceback = "".join(traceback.format_exception(
        exc_type, exc_value, exc_traceback
    ))

    return {
        "convertor_identifier": identifier,
        "message": str(exc_value),
        "traceback": formatted_traceback
    }


class CreatorsOperationFailed(Exception):
    """Raised when a creator process crashes in 'CreateContext'.

    The exception contains information about the creator and error. The data
    are prepared using 'prepare_failed_creator_operation_info' and can be
    serialized using json.

    Usage is for UI purposes which may not have access to exceptions directly
    and would not have ability to catch exceptions 'per creator'.

    Args:
        msg (str): General error message.
        failed_info (list[dict[str, Any]]): List of failed creators with
            exception message and optionally formatted traceback.
    """

    def __init__(self, msg, failed_info):
        super(CreatorsOperationFailed, self).__init__(msg)
        self.failed_info = failed_info


class CreatorsCollectionFailed(CreatorsOperationFailed):
    def __init__(self, failed_info):
        msg = "Failed to collect instances"
        super(CreatorsCollectionFailed, self).__init__(
            msg, failed_info
        )


class CreatorsSaveFailed(CreatorsOperationFailed):
    def __init__(self, failed_info):
        msg = "Failed update instance changes"
        super(CreatorsSaveFailed, self).__init__(
            msg, failed_info
        )


class CreatorsRemoveFailed(CreatorsOperationFailed):
    def __init__(self, failed_info):
        msg = "Failed to remove instances"
        super(CreatorsRemoveFailed, self).__init__(
            msg, failed_info
        )


class CreatorsCreateFailed(CreatorsOperationFailed):
    def __init__(self, failed_info):
        msg = "Failed to create instances"
        super(CreatorsCreateFailed, self).__init__(
            msg, failed_info
        )


def prepare_failed_creator_operation_info(
    identifier, label, exc_info, add_traceback=True
):
    formatted_traceback = None
    exc_type, exc_value, exc_traceback = exc_info
    if add_traceback:
        formatted_traceback = "".join(traceback.format_exception(
            exc_type, exc_value, exc_traceback
        ))

    return {
        "creator_identifier": identifier,
        "creator_label": label,
        "message": str(exc_value),
        "traceback": formatted_traceback
    }


_EMPTY_VALUE = object()


class TrackChangesItem(object):
    """Helper object to track changes in data.

    Has access to full old and new data and will create deep copy of them,
    so it is not needed to create copy before passed in.

    Can work as a dictionary if old or new value is a dictionary. In
    that case received object is another object of 'TrackChangesItem'.

    Goal is to be able to get old or new value as was or only changed values
    or get information about removed/changed keys, and all of that on
    any "dictionary level".

    ```
    # Example of possible usages
    >>> old_value = {
    ...     "key_1": "value_1",
    ...     "key_2": {
    ...         "key_sub_1": 1,
    ...         "key_sub_2": {
    ...             "enabled": True
    ...         }
    ...     },
    ...     "key_3": "value_2"
    ... }
    >>> new_value = {
    ...     "key_1": "value_1",
    ...     "key_2": {
    ...         "key_sub_2": {
    ...             "enabled": False
    ...         },
    ...         "key_sub_3": 3
    ...     },
    ...     "key_3": "value_3"
    ... }

    >>> changes = TrackChangesItem(old_value, new_value)
    >>> changes.changed
    True

    >>> changes["key_2"]["key_sub_1"].new_value is None
    True

    >>> list(sorted(changes.changed_keys))
    ['key_2', 'key_3']

    >>> changes["key_2"]["key_sub_2"]["enabled"].changed
    True

    >>> changes["key_2"].removed_keys
    {'key_sub_1'}

    >>> list(sorted(changes["key_2"].available_keys))
    ['key_sub_1', 'key_sub_2', 'key_sub_3']

    >>> changes.new_value == new_value
    True

    # Get only changed values
    only_changed_new_values = {
        key: changes[key].new_value
        for key in changes.changed_keys
    }
    ```

    Args:
        old_value (Any): Old value.
        new_value (Any): New value.
    """

    def __init__(self, old_value, new_value):
        self._changed = old_value != new_value
        # Resolve if value is '_EMPTY_VALUE' after comparison of the values
        if old_value is _EMPTY_VALUE:
            old_value = None
        if new_value is _EMPTY_VALUE:
            new_value = None
        self._old_value = copy.deepcopy(old_value)
        self._new_value = copy.deepcopy(new_value)

        self._old_is_dict = isinstance(old_value, dict)
        self._new_is_dict = isinstance(new_value, dict)

        self._old_keys = None
        self._new_keys = None
        self._available_keys = None
        self._removed_keys = None

        self._changed_keys = None

        self._sub_items = None

    def __getitem__(self, key):
        """Getter looks into subitems if object is dictionary."""

        if self._sub_items is None:
            self._prepare_sub_items()
        return self._sub_items[key]

    def __bool__(self):
        """Boolean of object is if old and new value are the same."""

        return self._changed

    def get(self, key, default=None):
        """Try to get sub item."""

        if self._sub_items is None:
            self._prepare_sub_items()
        return self._sub_items.get(key, default)

    @property
    def old_value(self):
        """Get copy of old value.

        Returns:
            Any: Whatever old value was.
        """

        return copy.deepcopy(self._old_value)

    @property
    def new_value(self):
        """Get copy of new value.

        Returns:
            Any: Whatever new value was.
        """

        return copy.deepcopy(self._new_value)

    @property
    def changed(self):
        """Value changed.

        Returns:
            bool: If data changed.
        """

        return self._changed

    @property
    def is_dict(self):
        """Object can be used as dictionary.

        Returns:
            bool: When can be used that way.
        """

        return self._old_is_dict or self._new_is_dict

    @property
    def changes(self):
        """Get changes in raw data.

        This method should be used only if 'is_dict' value is 'True'.

        Returns:
            Dict[str, Tuple[Any, Any]]: Changes are by key in tuple
                (<old value>, <new value>). If 'is_dict' is 'False' then
                output is always empty dictionary.
        """

        output = {}
        if not self.is_dict:
            return output

        old_value = self.old_value
        new_value = self.new_value
        for key in self.changed_keys:
            _old = None
            _new = None
            if self._old_is_dict:
                _old = old_value.get(key)
            if self._new_is_dict:
                _new = new_value.get(key)
            output[key] = (_old, _new)
        return output

    # Methods/properties that can be used when 'is_dict' is 'True'
    @property
    def old_keys(self):
        """Keys from old value.

        Empty set is returned if old value is not a dict.

        Returns:
            Set[str]: Keys from old value.
        """

        if self._old_keys is None:
            self._prepare_keys()
        return set(self._old_keys)

    @property
    def new_keys(self):
        """Keys from new value.

        Empty set is returned if old value is not a dict.

        Returns:
            Set[str]: Keys from new value.
        """

        if self._new_keys is None:
            self._prepare_keys()
        return set(self._new_keys)

    @property
    def changed_keys(self):
        """Keys that has changed from old to new value.

        Empty set is returned if both old and new value are not a dict.

        Returns:
            Set[str]: Keys of changed keys.
        """

        if self._changed_keys is None:
            self._prepare_sub_items()
        return set(self._changed_keys)

    @property
    def available_keys(self):
        """All keys that are available in old and new value.

        Empty set is returned if both old and new value are not a dict.
        Output is Union of 'old_keys' and 'new_keys'.

        Returns:
            Set[str]: All keys from old and new value.
        """

        if self._available_keys is None:
            self._prepare_keys()
        return set(self._available_keys)

    @property
    def removed_keys(self):
        """Key that are not available in new value but were in old value.

        Returns:
            Set[str]: All removed keys.
        """

        if self._removed_keys is None:
            self._prepare_sub_items()
        return set(self._removed_keys)

    def _prepare_keys(self):
        old_keys = set()
        new_keys = set()
        if self._old_is_dict and self._new_is_dict:
            old_keys = set(self._old_value.keys())
            new_keys = set(self._new_value.keys())

        elif self._old_is_dict:
            old_keys = set(self._old_value.keys())

        elif self._new_is_dict:
            new_keys = set(self._new_value.keys())

        self._old_keys = old_keys
        self._new_keys = new_keys
        self._available_keys = old_keys | new_keys
        self._removed_keys = old_keys - new_keys

    def _prepare_sub_items(self):
        sub_items = {}
        changed_keys = set()

        old_keys = self.old_keys
        new_keys = self.new_keys
        new_value = self.new_value
        old_value = self.old_value
        if self._old_is_dict and self._new_is_dict:
            for key in self.available_keys:
                item = TrackChangesItem(
                    old_value.get(key), new_value.get(key)
                )
                sub_items[key] = item
                if item.changed or key not in old_keys or key not in new_keys:
                    changed_keys.add(key)

        elif self._old_is_dict:
            old_keys = set(old_value.keys())
            available_keys = set(old_keys)
            changed_keys = set(available_keys)
            for key in available_keys:
                # NOTE Use '_EMPTY_VALUE' because old value could be 'None'
                #   which would result in "unchanged" item
                sub_items[key] = TrackChangesItem(
                    old_value.get(key), _EMPTY_VALUE
                )

        elif self._new_is_dict:
            new_keys = set(new_value.keys())
            available_keys = set(new_keys)
            changed_keys = set(available_keys)
            for key in available_keys:
                # NOTE Use '_EMPTY_VALUE' because new value could be 'None'
                #   which would result in "unchanged" item
                sub_items[key] = TrackChangesItem(
                    _EMPTY_VALUE, new_value.get(key)
                )

        self._sub_items = sub_items
        self._changed_keys = changed_keys


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


class AttributeValues(object):
    """Container which keep values of Attribute definitions.

    Goal is to have one object which hold values of attribute definitions for
    single instance.

    Has dictionary like methods. Not all of them are allowed all the time.

    Args:
        attr_defs(AbstractAttrDef): Defintions of value type and properties.
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
        value = self._data.pop(key, default)
        # Remove attribute definition if is 'UnknownDef'
        # - gives option to get rid of unknown values
        attr_def = self._attr_defs_by_key.get(key)
        if isinstance(attr_def, UnknownDef):
            self._attr_defs_by_key.pop(key)
            self._attr_defs.remove(attr_def)
        return value

    def reset_values(self):
        self._data = {}

    def mark_as_stored(self):
        self._origin_data = copy.deepcopy(self._data)

    @property
    def attr_defs(self):
        """Pointer to attribute definitions.

        Returns:
            List[AbstractAttrDef]: Attribute definitions.
        """

        return list(self._attr_defs)

    @property
    def origin_data(self):
        return copy.deepcopy(self._origin_data)

    def data_to_store(self):
        """Create new dictionary with data to store.

        Returns:
            Dict[str, Any]: Attribute values that should be stored.
        """

        output = {}
        for key in self._data:
            output[key] = self[key]

        for key, attr_def in self._attr_defs_by_key.items():
            if key not in output:
                output[key] = attr_def.default
        return output

    def get_serialized_attr_defs(self):
        """Serialize attribute definitions to json serializable types.

        Returns:
            List[Dict[str, Any]]: Serialized attribute definitions.
        """

        return serialize_attr_defs(self._attr_defs)


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
    Keep information about attribute definitions and their values.

    Args:
        parent(CreatedInstance, CreateContext): Parent for which will be
            data stored and from which are data loaded.
        origin_data(dict): Loaded data by plugin class name.
        attr_plugins(Union[List[pyblish.api.Plugin], None]): List of publish
            plugins that may have defined attribute definitions.
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

    def mark_as_stored(self):
        self._origin_data = copy.deepcopy(self.data_to_store())

    def data_to_store(self):
        """Convert attribute values to "data to store"."""

        output = {}
        for key, attr_value in self._data.items():
            output[key] = attr_value.data_to_store()
        return output

    @property
    def origin_data(self):
        return copy.deepcopy(self._origin_data)

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

    def serialize_attributes(self):
        return {
            "attr_defs": {
                plugin_name: attrs_value.get_serialized_attr_defs()
                for plugin_name, attrs_value in self._data.items()
            },
            "plugin_names_order": self._plugin_names_order,
            "missing_plugins": self._missing_plugins
        }

    def deserialize_attributes(self, data):
        self._plugin_names_order = data["plugin_names_order"]
        self._missing_plugins = data["missing_plugins"]

        attr_defs = deserialize_attr_defs(data["attr_defs"])

        origin_data = self._origin_data
        data = self._data
        self._data = {}

        added_keys = set()
        for plugin_name, attr_defs_data in attr_defs.items():
            attr_defs = deserialize_attr_defs(attr_defs_data)
            value = data.get(plugin_name) or {}
            orig_value = copy.deepcopy(origin_data.get(plugin_name) or {})
            self._data[plugin_name] = PublishAttributeValues(
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

    Notes:
        Object have 2 possible initialization. One using 'creator' object which
            is recommended for api usage. Second by passing information about
            creator.

    Args:
        family (str): Name of family that will be created.
        subset_name (str): Name of subset that will be created.
        data (Dict[str, Any]): Data used for filling subset name or override
            data from already existing instance.
        creator (Union[BaseCreator, None]): Creator responsible for instance.
        creator_identifier (str): Identifier of creator plugin.
        creator_label (str): Creator plugin label.
        group_label (str): Default group label from creator plugin.
        creator_attr_defs (List[AbstractAttrDef]): Attribute definitions from
            creator.
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
        self,
        family,
        subset_name,
        data,
        creator=None,
        creator_identifier=None,
        creator_label=None,
        group_label=None,
        creator_attr_defs=None,
    ):
        if creator is not None:
            creator_identifier = creator.identifier
            group_label = creator.get_group_label()
            creator_label = creator.label
            creator_attr_defs = creator.get_instance_attr_defs()

        self._creator_label = creator_label
        self._group_label = group_label or creator_identifier

        # Instance members may have actions on them
        # TODO implement members logic
        self._members = []

        # Data that can be used for lifetime of object
        self._transient_data = {}

        # Create a copy of passed data to avoid changing them on the fly
        data = copy.deepcopy(data or {})

        # Pop dictionary values that will be converted to objects to be able
        #   catch changes
        orig_creator_attributes = data.pop("creator_attributes", None) or {}
        orig_publish_attributes = data.pop("publish_attributes", None) or {}

        # Store original value of passed data
        self._orig_data = copy.deepcopy(data)

        # Pop family and subset to prevent unexpected changes
        # TODO change to 'productType' and 'productName' in AYON
        data.pop("family", None)
        data.pop("subset", None)

        if AYON_SERVER_ENABLED:
            asset_name = data.pop("asset", None)
            if "folderPath" not in data:
                data["folderPath"] = asset_name

        elif "folderPath" in data:
            asset_name = data.pop("folderPath").split("/")[-1]
            if "asset" not in data:
                data["asset"] = asset_name

        # QUESTION Does it make sense to have data stored as ordered dict?
        self._data = collections.OrderedDict()
        # QUESTION Do we need this "id" information on instance?
        self._data["id"] = "pyblish.avalon.instance"
        self._data["family"] = family
        self._data["subset"] = subset_name
        self._data["active"] = data.get("active", True)
        self._data["creator_identifier"] = creator_identifier

        # Pop from source data all keys that are defined in `_data` before
        #   this moment and through their values away
        # - they should be the same and if are not then should not change
        #   already set values
        for key in self._data.keys():
            if key in data:
                data.pop(key)

        self._data["variant"] = self._data.get("variant") or ""
        # Stored creator specific attribute values
        # {key: value}
        creator_values = copy.deepcopy(orig_creator_attributes)

        self._data["creator_attributes"] = CreatorAttributeValues(
            self,
            list(creator_attr_defs),
            creator_values,
            orig_creator_attributes
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
    def label(self):
        label = self._data.get("label")
        if not label:
            label = self.subset_name
        return label

    @property
    def group_label(self):
        label = self._data.get("group")
        if label:
            return label
        return self._group_label

    @property
    def origin_data(self):
        output = copy.deepcopy(self._orig_data)
        output["creator_attributes"] = self.creator_attributes.origin_data
        output["publish_attributes"] = self.publish_attributes.origin_data
        return output

    @property
    def creator_identifier(self):
        return self._data["creator_identifier"]

    @property
    def creator_label(self):
        return self._creator_label or self.creator_identifier

    @property
    def id(self):
        """Instance identifier.

        Returns:
            str: UUID of instance.
        """

        return self._data["instance_id"]

    @property
    def data(self):
        """Legacy access to data.

        Access to data is needed to modify values.

        Returns:
            CreatedInstance: Object can be used as dictionary but with
                validations of immutable keys.
        """

        return self

    @property
    def transient_data(self):
        """Data stored for lifetime of instance object.

        These data are not stored to scene and will be lost on object
        deletion.

        Can be used to store objects. In some host implementations is not
        possible to reference to object in scene with some unique identifier
        (e.g. node in Fusion.). In that case it is handy to store the object
        here. Should be used that way only if instance data are stored on the
        node itself.

        Returns:
            Dict[str, Any]: Dictionary object where you can store data related
                to instance for lifetime of instance object.
        """

        return self._transient_data

    def changes(self):
        """Calculate and return changes."""

        return TrackChangesItem(self.origin_data, self.data_to_store())

    def mark_as_stored(self):
        """Should be called when instance data are stored.

        Origin data are replaced by current data so changes are cleared.
        """

        orig_keys = set(self._orig_data.keys())
        for key, value in self._data.items():
            orig_keys.discard(key)
            if key in ("creator_attributes", "publish_attributes"):
                continue
            self._orig_data[key] = copy.deepcopy(value)

        for key in orig_keys:
            self._orig_data.pop(key)

        self.creator_attributes.mark_as_stored()
        self.publish_attributes.mark_as_stored()

    @property
    def creator_attributes(self):
        return self._data["creator_attributes"]

    @property
    def creator_attribute_defs(self):
        """Attribute definitions defined by creator plugin.

        Returns:
              List[AbstractAttrDef]: Attribute definitions.
        """

        return self.creator_attributes.attr_defs

    @property
    def publish_attributes(self):
        return self._data["publish_attributes"]

    def data_to_store(self):
        """Collect data that contain json parsable types.

        It is possible to recreate the instance using these data.

        Todos:
            We probably don't need OrderedDict. When data are loaded they
                are not ordered anymore.

        Returns:
            OrderedDict: Ordered dictionary with instance data.
        """

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
        """Convert instance data from workfile to CreatedInstance.

        Args:
            instance_data (Dict[str, Any]): Data in a structure ready for
                'CreatedInstance' object.
            creator (BaseCreator): Creator plugin which is creating the
                instance of for which the instance belong.
        """

        instance_data = copy.deepcopy(instance_data)

        family = instance_data.get("family", None)
        if family is None:
            family = creator.family
        subset_name = instance_data.get("subset", None)

        return cls(
            family, subset_name, instance_data, creator
        )

    def set_publish_plugins(self, attr_plugins):
        """Set publish plugins with attribute definitions.

        This method should be called only from 'CreateContext'.

        Args:
            attr_plugins (List[pyblish.api.Plugin]): Pyblish plugins which
                inherit from 'OpenPypePyblishPluginMixin' and may contain
                attribute definitions.
        """

        self.publish_attributes.set_publish_plugins(attr_plugins)

    def add_members(self, members):
        """Currently unused method."""

        for member in members:
            if member not in self._members:
                self._members.append(member)

    def serialize_for_remote(self):
        """Serialize object into data to be possible recreated object.

        Returns:
            Dict[str, Any]: Serialized data.
        """

        creator_attr_defs = self.creator_attributes.get_serialized_attr_defs()
        publish_attributes = self.publish_attributes.serialize_attributes()
        return {
            "data": self.data_to_store(),
            "orig_data": self.origin_data,
            "creator_attr_defs": creator_attr_defs,
            "publish_attributes": publish_attributes,
            "creator_label": self._creator_label,
            "group_label": self._group_label,
        }

    @classmethod
    def deserialize_on_remote(cls, serialized_data):
        """Convert instance data to CreatedInstance.

        This is fake instance in remote process e.g. in UI process. The creator
        is not a full creator and should not be used for calling methods when
        instance is created from this method (matters on implementation).

        Args:
            serialized_data (Dict[str, Any]): Serialized data for remote
                recreating. Should contain 'data' and 'orig_data'.
        """

        instance_data = copy.deepcopy(serialized_data["data"])
        creator_identifier = instance_data["creator_identifier"]

        family = instance_data["family"]
        subset_name = instance_data.get("subset", None)

        creator_label = serialized_data["creator_label"]
        group_label = serialized_data["group_label"]
        creator_attr_defs = deserialize_attr_defs(
            serialized_data["creator_attr_defs"]
        )
        publish_attributes = serialized_data["publish_attributes"]

        obj = cls(
            family,
            subset_name,
            instance_data,
            creator_identifier=creator_identifier,
            creator_label=creator_label,
            group_label=group_label,
            creator_attr_defs=creator_attr_defs
        )
        obj._orig_data = serialized_data["orig_data"]
        obj.publish_attributes.deserialize_attributes(publish_attributes)

        return obj

    # Context validation related methods/properties
    @property
    def has_set_asset(self):
        """Asset name is set in data."""

        if AYON_SERVER_ENABLED:
            return "folderPath" in self._data
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


class ConvertorItem(object):
    """Item representing convertor plugin.

    Args:
        identifier (str): Identifier of convertor.
        label (str): Label which will be shown in UI.
    """

    def __init__(self, identifier, label):
        self._id = str(uuid4())
        self.identifier = identifier
        self.label = label

    @property
    def id(self):
        return self._id

    def to_data(self):
        return {
            "id": self.id,
            "identifier": self.identifier,
            "label": self.label
        }

    @classmethod
    def from_data(cls, data):
        obj = cls(data["identifier"], data["label"])
        obj._id = data["id"]
        return obj


class CreateContext:
    """Context of instance creation.

    Context itself also can store data related to whole creation (workfile).
    - those are mainly for Context publish plugins

    Todos:
        Don't use 'AvalonMongoDB'. It's used only to keep track about current
            context which should be handled by host.

    Args:
        host(ModuleType): Host implementation which handles implementation and
            global metadata.
        headless(bool): Context is created out of UI (Current not used).
        reset(bool): Reset context on initialization.
        discover_publish_plugins(bool): Discover publish plugins during reset
            phase.
    """

    def __init__(
        self, host, headless=False, reset=True, discover_publish_plugins=True
    ):
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

        self._current_project_name = None
        self._current_asset_name = None
        self._current_task_name = None
        self._current_workfile_path = None

        self._current_project_anatomy = None

        self._host_is_valid = host_is_valid
        # Currently unused variable
        self.headless = headless

        # Instances by their ID
        self._instances_by_id = {}

        self.creator_discover_result = None
        self.convertor_discover_result = None
        # Discovered creators
        self.creators = {}
        # Prepare categories of creators
        self.autocreators = {}
        # Manual creators
        self.manual_creators = {}
        # Creators that are disabled
        self.disabled_creators = {}

        self.convertors_plugins = {}
        self.convertor_items_by_id = {}

        self.publish_discover_result = None
        self.publish_plugins_mismatch_targets = []
        self.publish_plugins = []
        self.plugins_with_defs = []
        self._attr_plugins_by_family = {}

        # Helpers for validating context of collected instances
        #   - they can be validation for multiple instances at one time
        #       using context manager which will trigger validation
        #       after leaving of last context manager scope
        self._bulk_counter = 0
        self._bulk_instances_to_process = []

        # Shared data across creators during collection phase
        self._collection_shared_data = None

        self.thumbnail_paths_by_instance_id = {}

        # Trigger reset if was enabled
        if reset:
            self.reset(discover_publish_plugins)

    @property
    def instances(self):
        return self._instances_by_id.values()

    @property
    def instances_by_id(self):
        return self._instances_by_id

    @property
    def publish_attributes(self):
        """Access to global publish attributes."""
        return self._publish_attributes

    def get_instance_by_id(self, instance_id):
        """Receive instance by id.

        Args:
            instance_id (str): Instance id.

        Returns:
            Union[CreatedInstance, None]: Instance or None if instance with
                given id is not available.
        """

        return self._instances_by_id.get(instance_id)

    def get_sorted_creators(self, identifiers=None):
        """Sorted creators by 'order' attribute.

        Args:
            identifiers (Iterable[str]): Filter creators by identifiers. All
                creators are returned if 'None' is passed.

        Returns:
            List[BaseCreator]: Sorted creator plugins by 'order' value.
        """

        if identifiers is not None:
            identifiers = set(identifiers)
            creators = [
                creator
                for identifier, creator in self.creators.items()
                if identifier in identifiers
            ]
        else:
            creators = self.creators.values()

        return sorted(
            creators, key=lambda creator: creator.order
        )

    @property
    def sorted_creators(self):
        """Sorted creators by 'order' attribute.

        Returns:
            List[BaseCreator]: Sorted creator plugins by 'order' value.
        """

        return self.get_sorted_creators()

    @property
    def sorted_autocreators(self):
        """Sorted auto-creators by 'order' attribute.

        Returns:
            List[AutoCreator]: Sorted plugins by 'order' value.
        """

        return sorted(
            self.autocreators.values(), key=lambda creator: creator.order
        )

    @classmethod
    def get_host_misssing_methods(cls, host):
        """Collect missing methods from host.

        Args:
            host(ModuleType): Host implementaion.
        """

        missing = set(
            IPublishHost.get_missing_publish_methods(host)
        )
        return missing

    @property
    def host_is_valid(self):
        """Is host valid for creation."""
        return self._host_is_valid

    @property
    def host_name(self):
        if hasattr(self.host, "name"):
            return self.host.name
        return os.environ["AVALON_APP"]

    def get_current_project_name(self):
        """Project name which was used as current context on context reset.

        Returns:
            Union[str, None]: Project name.
        """

        return self._current_project_name

    def get_current_asset_name(self):
        """Asset name which was used as current context on context reset.

        Returns:
            Union[str, None]: Asset name.
        """

        return self._current_asset_name

    def get_current_task_name(self):
        """Task name which was used as current context on context reset.

        Returns:
            Union[str, None]: Task name.
        """

        return self._current_task_name

    def get_current_workfile_path(self):
        """Workfile path which was opened on context reset.

        Returns:
            Union[str, None]: Workfile path.
        """

        return self._current_workfile_path

    def get_current_project_anatomy(self):
        """Project anatomy for current project.

        Returns:
            Anatomy: Anatomy object ready to be used.
        """

        if self._current_project_anatomy is None:
            self._current_project_anatomy = Anatomy(
                self._current_project_name)
        return self._current_project_anatomy

    @property
    def context_has_changed(self):
        """Host context has changed.

        As context is used project, asset, task name and workfile path if
        host does support workfiles.

        Returns:
            bool: Context changed.
        """

        project_name, asset_name, task_name, workfile_path = (
            self._get_current_host_context()
        )
        return (
            self._current_project_name != project_name
            or self._current_asset_name != asset_name
            or self._current_task_name != task_name
            or self._current_workfile_path != workfile_path
        )

    project_name = property(get_current_project_name)
    project_anatomy = property(get_current_project_anatomy)

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

        self.reset_preparation()

        self.reset_current_context()
        self.reset_plugins(discover_publish_plugins)
        self.reset_context_data()

        with self.bulk_instances_collection():
            self.reset_instances()
            self.find_convertor_items()
            self.execute_autocreators()

        self.reset_finalization()

    def refresh_thumbnails(self):
        """Cleanup thumbnail paths.

        Remove all thumbnail filepaths that are empty or lead to files which
        does not exists or of instances that are not available anymore.
        """

        invalid = set()
        for instance_id, path in self.thumbnail_paths_by_instance_id.items():
            instance_available = True
            if instance_id is not None:
                instance_available = instance_id in self._instances_by_id

            if (
                not instance_available
                or not path
                or not os.path.exists(path)
            ):
                invalid.add(instance_id)

        for instance_id in invalid:
            self.thumbnail_paths_by_instance_id.pop(instance_id)

    def reset_preparation(self):
        """Prepare attributes that must be prepared/cleaned before reset."""

        # Give ability to store shared data for collection phase
        self._collection_shared_data = {}

    def reset_finalization(self):
        """Cleanup of attributes after reset."""

        # Stop access to collection shared data
        self._collection_shared_data = None
        self.refresh_thumbnails()

    def _get_current_host_context(self):
        project_name = asset_name = task_name = workfile_path = None
        if hasattr(self.host, "get_current_context"):
            host_context = self.host.get_current_context()
            if host_context:
                project_name = host_context.get("project_name")
                asset_name = host_context.get("asset_name")
                task_name = host_context.get("task_name")

        if isinstance(self.host, IWorkfileHost):
            workfile_path = self.host.get_current_workfile()

        # --- TODO remove these conditions ---
        if not project_name:
            project_name = legacy_io.Session.get("AVALON_PROJECT")
        if not asset_name:
            asset_name = legacy_io.Session.get("AVALON_ASSET")
        if not task_name:
            task_name = legacy_io.Session.get("AVALON_TASK")
        # ---
        return project_name, asset_name, task_name, workfile_path

    def reset_current_context(self):
        """Refresh current context.

        Reset is based on optional host implementation of `get_current_context`
        function or using `legacy_io.Session`.

        Some hosts have ability to change context file without using workfiles
        tool but that change is not propagated to 'legacy_io.Session'
        nor 'os.environ'.

        Todos:
            UI: Current context should be also checked on save - compare
                initial values vs. current values.
            Related to UI checks: Current workfile can be also considered
                as current context information as that's where the metadata
                are stored. We should store the workfile (if is available) too.
        """

        project_name, asset_name, task_name, workfile_path = (
            self._get_current_host_context()
        )

        self._current_project_name = project_name
        self._current_asset_name = asset_name
        self._current_task_name = task_name
        self._current_workfile_path = workfile_path

        self._current_project_anatomy = None

    def reset_plugins(self, discover_publish_plugins=True):
        """Reload plugins.

        Reloads creators from preregistered paths and can load publish plugins
        if it's enabled on context.
        """

        self._reset_publish_plugins(discover_publish_plugins)
        self._reset_creator_plugins()
        self._reset_convertor_plugins()

    def _reset_publish_plugins(self, discover_publish_plugins):
        from openpype.pipeline import OpenPypePyblishPluginMixin
        from openpype.pipeline.publish import (
            publish_plugins_discover
        )

        # Reset publish plugins
        self._attr_plugins_by_family = {}

        discover_result = DiscoverResult(pyblish.api.Plugin)
        plugins_with_defs = []
        plugins_by_targets = []
        plugins_mismatch_targets = []
        if discover_publish_plugins:
            discover_result = publish_plugins_discover()
            publish_plugins = discover_result.plugins

            targets = set(pyblish.logic.registered_targets())
            targets.add("default")
            plugins_by_targets = pyblish.logic.plugins_by_targets(
                publish_plugins, list(targets)
            )

            # Collect plugins that can have attribute definitions
            for plugin in publish_plugins:
                if OpenPypePyblishPluginMixin in inspect.getmro(plugin):
                    plugins_with_defs.append(plugin)

            plugins_mismatch_targets = [
                plugin
                for plugin in publish_plugins
                if plugin not in plugins_by_targets
            ]

        self.publish_plugins_mismatch_targets = plugins_mismatch_targets
        self.publish_discover_result = discover_result
        self.publish_plugins = plugins_by_targets
        self.plugins_with_defs = plugins_with_defs

    def _reset_creator_plugins(self):
        # Prepare settings
        system_settings = get_system_settings()
        project_settings = get_project_settings(self.project_name)

        # Discover and prepare creators
        creators = {}
        disabled_creators = {}
        autocreators = {}
        manual_creators = {}
        report = discover_creator_plugins(return_report=True)
        self.creator_discover_result = report
        for creator_class in report.plugins:
            if inspect.isabstract(creator_class):
                self.log.debug(
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
                    "Creator's host name \"{}\""
                    " is not supported for current host \"{}\""
                ).format(creator_class.host_name, self.host_name))
                continue

            creator = creator_class(
                project_settings,
                system_settings,
                self,
                self.headless
            )

            if not creator.enabled:
                disabled_creators[creator_identifier] = creator
                continue
            creators[creator_identifier] = creator
            if isinstance(creator, AutoCreator):
                autocreators[creator_identifier] = creator
            elif isinstance(creator, Creator):
                manual_creators[creator_identifier] = creator

        self.autocreators = autocreators
        self.manual_creators = manual_creators

        self.creators = creators
        self.disabled_creators = disabled_creators

    def _reset_convertor_plugins(self):
        convertors_plugins = {}
        report = discover_convertor_plugins(return_report=True)
        self.convertor_discover_result = report
        for convertor_class in report.plugins:
            if inspect.isabstract(convertor_class):
                self.log.info(
                    "Skipping abstract Creator {}".format(str(convertor_class))
                )
                continue

            convertor_identifier = convertor_class.identifier
            if convertor_identifier in convertors_plugins:
                self.log.warning((
                    "Duplicated Converter identifier. "
                    "Using first and skipping following"
                ))
                continue

            convertors_plugins[convertor_identifier] = convertor_class(self)

        self.convertors_plugins = convertors_plugins

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

        return TrackChangesItem(
            self._original_context_data, self.context_data_to_store()
        )

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
            instance.family
        )
        instance.set_publish_plugins(attr_plugins)

        # Add instance to be validated inside 'bulk_instances_collection'
        #   context manager if is inside bulk
        with self.bulk_instances_collection():
            self._bulk_instances_to_process.append(instance)

    def _get_creator_in_create(self, identifier):
        """Creator by identifier with unified error.

        Helper method to get creator by identifier with same error when creator
        is not available.

        Args:
            identifier (str): Identifier of creator plugin.

        Returns:
            BaseCreator: Creator found by identifier.

        Raises:
            CreatorError: When identifier is not known.
        """

        creator = self.creators.get(identifier)
        # Fake CreatorError (Could be maybe specific exception?)
        if creator is None:
            raise CreatorError(
                "Creator {} was not found".format(identifier)
            )
        return creator

    def create(
        self,
        creator_identifier,
        variant,
        asset_doc=None,
        task_name=None,
        pre_create_data=None
    ):
        """Trigger create of plugins with standartized arguments.

        Arguments 'asset_doc' and 'task_name' use current context as default
        values. If only 'task_name' is provided it will be overriden by
        task name from current context. If 'task_name' is not provided
        when 'asset_doc' is, it is considered that task name is not specified,
        which can lead to error if subset name template requires task name.

        Args:
            creator_identifier (str): Identifier of creator plugin.
            variant (str): Variant used for subset name.
            asset_doc (Dict[str, Any]): Asset document which define context of
                creation (possible context of created instance/s).
            task_name (str): Name of task to which is context related.
            pre_create_data (Dict[str, Any]): Pre-create attribute values.

        Returns:
            Any: Output of triggered creator's 'create' method.

        Raises:
            CreatorError: If creator was not found or asset is empty.
        """

        creator = self._get_creator_in_create(creator_identifier)

        project_name = self.project_name
        if asset_doc is None:
            asset_name = self.get_current_asset_name()
            asset_doc = get_asset_by_name(project_name, asset_name)
            task_name = self.get_current_task_name()
            if asset_doc is None:
                raise CreatorError(
                    "Asset with name {} was not found".format(asset_name)
                )

        if pre_create_data is None:
            pre_create_data = {}

        precreate_attr_defs = []
        # Hidden creators do not have or need the pre-create attributes.
        if isinstance(creator, Creator):
            precreate_attr_defs = creator.get_pre_create_attr_defs()

        # Create default values of precreate data
        _pre_create_data = get_default_values(precreate_attr_defs)
        # Update passed precreate data to default values
        # TODO validate types
        _pre_create_data.update(pre_create_data)

        subset_name = creator.get_subset_name(
            variant,
            task_name,
            asset_doc,
            project_name,
            self.host_name
        )
        asset_name = get_asset_name_identifier(asset_doc)
        if AYON_SERVER_ENABLED:
            asset_name_key = "folderPath"
        else:
            asset_name_key = "asset"

        instance_data = {
            asset_name_key: asset_name,
            "task": task_name,
            "family": creator.family,
            "variant": variant
        }
        return creator.create(
            subset_name,
            instance_data,
            _pre_create_data
        )

    def _create_with_unified_error(
        self, identifier, creator, *args, **kwargs
    ):
        error_message = "Failed to run Creator with identifier \"{}\". {}"

        label = None
        add_traceback = False
        result = None
        fail_info = None
        success = False

        try:
            # Try to get creator and his label
            if creator is None:
                creator = self._get_creator_in_create(identifier)
            label = getattr(creator, "label", label)

            # Run create
            result = creator.create(*args, **kwargs)
            success = True

        except CreatorError:
            exc_info = sys.exc_info()
            self.log.warning(error_message.format(identifier, exc_info[1]))

        except:
            add_traceback = True
            exc_info = sys.exc_info()
            self.log.warning(
                error_message.format(identifier, ""),
                exc_info=True
            )

        if not success:
            fail_info = prepare_failed_creator_operation_info(
                identifier, label, exc_info, add_traceback
            )
        return result, fail_info

    def create_with_unified_error(self, identifier, *args, **kwargs):
        """Trigger create but raise only one error if anything fails.

        Added to raise unified exception. Capture any possible issues and
        reraise it with unified information.

        Args:
            identifier (str): Identifier of creator.
            *args (Tuple[Any]): Arguments for create method.
            **kwargs (Dict[Any, Any]): Keyword argument for create method.

        Raises:
            CreatorsCreateFailed: When creation fails due to any possible
                reason. If anything goes wrong this is only possible exception
                the method should raise.
        """

        result, fail_info = self._create_with_unified_error(
            identifier, None, *args, **kwargs
        )
        if fail_info is not None:
            raise CreatorsCreateFailed([fail_info])
        return result

    def _remove_instance(self, instance):
        self._instances_by_id.pop(instance.id, None)

    def creator_removed_instance(self, instance):
        """When creator removes instance context should be acknowledged.

        If creator removes instance conext should know about it to avoid
        possible issues in the session.

        Args:
            instance (CreatedInstance): Object of instance which was removed
                from scene metadata.
        """

        self._remove_instance(instance)

    def add_convertor_item(self, convertor_identifier, label):
        self.convertor_items_by_id[convertor_identifier] = ConvertorItem(
            convertor_identifier, label
        )

    def remove_convertor_item(self, convertor_identifier):
        self.convertor_items_by_id.pop(convertor_identifier, None)

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
        self._instances_by_id = collections.OrderedDict()

        # Collect instances
        error_message = "Collection of instances for creator {} failed. {}"
        failed_info = []
        for creator in self.sorted_creators:
            label = creator.label
            identifier = creator.identifier
            failed = False
            add_traceback = False
            exc_info = None
            try:
                creator.collect_instances()

            except CreatorError:
                failed = True
                exc_info = sys.exc_info()
                self.log.warning(error_message.format(identifier, exc_info[1]))

            except:
                failed = True
                add_traceback = True
                exc_info = sys.exc_info()
                self.log.warning(
                    error_message.format(identifier, ""),
                    exc_info=True
                )

            if failed:
                failed_info.append(
                    prepare_failed_creator_operation_info(
                        identifier, label, exc_info, add_traceback
                    )
                )

        if failed_info:
            raise CreatorsCollectionFailed(failed_info)

    def find_convertor_items(self):
        """Go through convertor plugins to look for items to convert.

        Raises:
            ConvertorsFindFailed: When one or more convertors fails during
                finding.
        """

        self.convertor_items_by_id = {}

        failed_info = []
        for convertor in self.convertors_plugins.values():
            try:
                convertor.find_instances()

            except:
                failed_info.append(
                    prepare_failed_convertor_operation_info(
                        convertor.identifier, sys.exc_info()
                    )
                )
                self.log.warning(
                    "Failed to find instances of convertor \"{}\"".format(
                        convertor.identifier
                    ),
                    exc_info=True
                )

        if failed_info:
            raise ConvertorsFindFailed(failed_info)

    def execute_autocreators(self):
        """Execute discovered AutoCreator plugins.

        Reset instances if any autocreator executed properly.
        """

        failed_info = []
        for creator in self.sorted_autocreators:
            identifier = creator.identifier
            _, fail_info = self._create_with_unified_error(identifier, creator)
            if fail_info is not None:
                failed_info.append(fail_info)

        if failed_info:
            raise CreatorsCreateFailed(failed_info)

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
            if AYON_SERVER_ENABLED:
                asset_name = instance.get("folderPath")
            else:
                asset_name = instance.get("asset")
            if asset_name:
                task_names_by_asset_name[asset_name] = set()
                if task_name:
                    task_names_by_asset_name[asset_name].add(task_name)

        asset_names = {
            asset_name
            for asset_name in task_names_by_asset_name.keys()
            if asset_name is not None
        }
        fields = {"name", "data.tasks"}
        if AYON_SERVER_ENABLED:
            fields |= {"data.parents"}
        asset_docs = list(get_assets(
            self.project_name,
            asset_names=asset_names,
            fields=fields
        ))

        task_names_by_asset_name = {}
        asset_docs_by_name = collections.defaultdict(list)
        for asset_doc in asset_docs:
            asset_name = get_asset_name_identifier(asset_doc)
            tasks = asset_doc.get("data", {}).get("tasks") or {}
            task_names_by_asset_name[asset_name] = set(tasks.keys())
            asset_docs_by_name[asset_doc["name"]].append(asset_doc)

        for instance in instances:
            if not instance.has_valid_asset or not instance.has_valid_task:
                continue

            if AYON_SERVER_ENABLED:
                asset_name = instance["folderPath"]
                if asset_name and "/" not in asset_name:
                    asset_docs = asset_docs_by_name.get(asset_name)
                    if len(asset_docs) == 1:
                        asset_name = get_asset_name_identifier(asset_docs[0])
                        instance["folderPath"] = asset_name
            else:
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
            instance_changes = instance.changes()
            if not instance_changes:
                continue

            identifier = instance.creator_identifier
            instances_by_identifier[identifier].append(
                UpdateData(instance, instance_changes)
            )

        if not instances_by_identifier:
            return

        error_message = "Instances update of creator \"{}\" failed. {}"
        failed_info = []

        for creator in self.get_sorted_creators(
            instances_by_identifier.keys()
        ):
            identifier = creator.identifier
            update_list = instances_by_identifier[identifier]
            if not update_list:
                continue

            label = creator.label
            failed = False
            add_traceback = False
            exc_info = None
            try:
                creator.update_instances(update_list)

            except CreatorError:
                failed = True
                exc_info = sys.exc_info()
                self.log.warning(error_message.format(identifier, exc_info[1]))

            except:
                failed = True
                add_traceback = True
                exc_info = sys.exc_info()
                self.log.warning(
                    error_message.format(identifier, ""), exc_info=True)

            if failed:
                failed_info.append(
                    prepare_failed_creator_operation_info(
                        identifier, label, exc_info, add_traceback
                    )
                )
            else:
                for update_data in update_list:
                    instance = update_data.instance
                    instance.mark_as_stored()

        if failed_info:
            raise CreatorsSaveFailed(failed_info)

    def remove_instances(self, instances):
        """Remove instances from context.

        All instances that don't have creator identifier leading to existing
            creator are just removed from context.

        Args:
            instances(List[CreatedInstance]): Instances that should be removed.
                Remove logic is done using creator, which may require to
                do other cleanup than just remove instance from context.
        """

        instances_by_identifier = collections.defaultdict(list)
        for instance in instances:
            identifier = instance.creator_identifier
            instances_by_identifier[identifier].append(instance)

        # Just remove instances from context if creator is not available
        missing_creators = set(instances_by_identifier) - set(self.creators)
        for identifier in missing_creators:
            for instance in instances_by_identifier[identifier]:
                self._remove_instance(instance)

        error_message = "Instances removement of creator \"{}\" failed. {}"
        failed_info = []
        # Remove instances by creator plugin order
        for creator in self.get_sorted_creators(
            instances_by_identifier.keys()
        ):
            identifier = creator.identifier
            creator_instances = instances_by_identifier[identifier]

            label = creator.label
            failed = False
            add_traceback = False
            exc_info = None
            try:
                creator.remove_instances(creator_instances)

            except CreatorError:
                failed = True
                exc_info = sys.exc_info()
                self.log.warning(
                    error_message.format(identifier, exc_info[1])
                )

            except:
                failed = True
                add_traceback = True
                exc_info = sys.exc_info()
                self.log.warning(
                    error_message.format(identifier, ""),
                    exc_info=True
                )

            if failed:
                failed_info.append(
                    prepare_failed_creator_operation_info(
                        identifier, label, exc_info, add_traceback
                    )
                )

        if failed_info:
            raise CreatorsRemoveFailed(failed_info)

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
        """Publish plugins attributes for Context plugins.

        Returns:
            List[pyblish.api.Plugin]: Publish plugins that have attribute
                definitions for context.
        """

        plugins = []
        for plugin in self.plugins_with_defs:
            if not plugin.__instanceEnabled__:
                plugins.append(plugin)
        return plugins

    @property
    def collection_shared_data(self):
        """Access to shared data that can be used during creator's collection.

        Retruns:
            Dict[str, Any]: Shared data.

        Raises:
            UnavailableSharedData: When called out of collection phase.
        """

        if self._collection_shared_data is None:
            raise UnavailableSharedData(
                "Accessed Collection shared data out of collection phase"
            )
        return self._collection_shared_data

    def run_convertor(self, convertor_identifier):
        """Run convertor plugin by identifier.

        Conversion is skipped if convertor is not available.

        Args:
            convertor_identifier (str): Identifier of convertor.
        """

        convertor = self.convertors_plugins.get(convertor_identifier)
        if convertor is not None:
            convertor.convert()

    def run_convertors(self, convertor_identifiers):
        """Run convertor plugins by identifiers.

        Conversion is skipped if convertor is not available. It is recommended
        to trigger reset after conversion to reload instances.

        Args:
            convertor_identifiers (Iterator[str]): Identifiers of convertors
                to run.

        Raises:
            ConvertorsConversionFailed: When one or more convertors fails.
        """

        failed_info = []
        for convertor_identifier in convertor_identifiers:
            try:
                self.run_convertor(convertor_identifier)

            except:
                failed_info.append(
                    prepare_failed_convertor_operation_info(
                        convertor_identifier, sys.exc_info()
                    )
                )
                self.log.warning(
                    "Failed to convert instances of convertor \"{}\"".format(
                        convertor_identifier
                    ),
                    exc_info=True
                )

        if failed_info:
            raise ConvertorsConversionFailed(failed_info)
