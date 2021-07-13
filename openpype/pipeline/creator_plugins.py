import copy
import logging
import contextlib
import collections
from uuid import uuid4

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty
)
import six

from .lib import UnknownDef
from openpype.lib import get_subset_name


class FamilyAttributeValues:
    def __init__(self, instance, values):
        self.instance = instance
        creator = self.instance.creator

        if creator is not None:
            attr_defs = creator.get_attribute_defs()
        else:
            attr_defs = [
                UnknownDef(key, label=key, default=value)
                for key, value in values.items()
            ]

        self._attr_defs = attr_defs
        self._attr_defs_by_key = {}
        self._data = {}
        for attr_def in attr_defs:
            key = attr_def.key
            self._attr_defs_by_key[key] = attr_def
            self._data[key] = values.get(key)

        self._last_data = copy.deepcopy(values)

        self._chunk_value = 0

    def __setitem__(self, key, value):
        if key not in self._attr_defs_by_key:
            raise KeyError("Key \"{}\" was not found.".format(key))

        old_value = self._data.get(key)
        if old_value == value:
            return
        self._data[key] = value

        self._propagate_changes({
            key: (old_value, value)
        })

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
        with self.chunk_changes():
            for _key, _value in dict(value):
                self[_key] = _value

    def pop(self, key, default=None):
        if key not in self._data:
            return default

        result = self._data.pop(key)
        self._propagate_changes({
            key: (result, None)
        })
        return result

    @property
    def attr_defs(self):
        return self._attr_defs

    @staticmethod
    def calculate_changes(new_data, old_data):
        changes = {}
        for key, new_value in new_data.items():
            old_value = old_data.get(key)
            if old_value != new_value:
                changes[key] = (old_value, new_value)
        return changes

    def changes(self):
        return self.calculate_changes(self._data, self._last_data)

    def _propagate_changes(self, changes=None):
        if self._chunk_value > 0:
            return

        if changes is None:
            changes = self.changes()

        if not changes:
            return

        self.instance.on_family_attribute_change(changes)
        for key, values in changes.items():
            self._last_data[key] = values[1]

    @contextlib.contextmanager
    def chunk_changes(self):
        try:
            self._chunk_value += 1
            yield
        finally:
            self._chunk_value -= 1

        if self._chunk_value == 0:
            self._propagate_changes()


class AvalonInstance:
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
        self, host, creator, family, subset_name, data=None, new=True
    ):
        self.host = host
        self.creator = creator

        # Family of instance
        self.family = family
        # Subset name
        self.subset_name = subset_name

        # Create a copy of passed data to avoid changing them on the fly
        data = copy.deepcopy(data or {})
        # Store original value of passed data
        self._orig_data = copy.deepcopy(data)

        # Pop family and subset to preved unexpected changes
        data.pop("family", None)
        data.pop("subset", None)

        # Pop dictionary values that will be converted to objects to be able
        #   catch changes
        orig_family_attributes = data.pop("family_attributes") or {}
        orig_publish_attributes = data.pop("publish_attributes") or {}

        self._data = collections.OrderedDict()
        self._data["id"] = "pyblish.avalon.instance"
        self._data["family"] = family
        self._data["subset"] = subset_name
        self._data["active"] = data.get("active", True)

        # Schema or version?
        if new:
            self._data["version"] = 1
        else:
            self._data["version"] = data.get("version")

        # Stored family specific attribute values
        # {key: value}
        self._data["family_attributes"] = FamilyAttributeValues(
            self, orig_family_attributes
        )

        # Stored publish specific attribute values
        # {<plugin name>: {key: value}}
        self._data["publish_attributes"] = {}
        if data:
            self._data.update(data)

        if not self._data.get("uuid"):
            self._data["uuid"] = str(uuid4())

    @property
    def data(self):
        return self._data

    @property
    def family_attribute_defs(self):
        return self._data["family_attributes"].attr_defs

    def on_family_attribute_change(self, changes):
        print(changes)

    def change_order(self, keys_order):
        data = collections.OrderedDict()
        for key in keys_order:
            if key in self.data:
                data[key] = self.data.pop(key)

        for key in tuple(self.data.keys()):
            data[key] = self.data.pop(key)
        self.data = data

    @classmethod
    def from_existing(cls, host, creator, instance_data):
        """Convert instance data from workfile to AvalonInstance."""
        instance_data = copy.deepcopy(instance_data)

        family = instance_data.get("family", None)
        subset_name = instance_data.get("subset", None)

        return cls(
            host, creator, family, subset_name, instance_data, new=False
        )



@six.add_metaclass(ABCMeta)
class BaseCreator:
    """Plugin that create and modify instance data before publishing process.

    We should maybe find better name as creation is only one part of it's logic
    and to avoid expectations that it is the same as `avalon.api.Creator`.

    Single object should be used for multiple instances instead of single
    instance per one creator object. Do not store temp data or mid-process data
    to `self` if it's not Plugin specific.
    """

    # Variable to store logger
    _log = None

    # Creator is enabled (Probably does not have reason of existence?)
    enabled = True

    # GUI Purposes
    # - default_variants may not be used if `get_default_variants` is overriden
    default_variants = []

    def __init__(self, system_settings, project_settings, headless=False):
        # Creator is running in headless mode (without UI elemets)
        # - we may use UI inside processing this attribute should be checked
        self.headless = headless

    @abstractproperty
    def family(self):
        """Family that plugin represents."""
        pass

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @abstractmethod
    def create(self, options=None):
        """Create new instance.

        Replacement of `process` method from avalon implementation.
        - must expect all data that were passed to init in previous
            implementation
        """
        pass

    def get_default_variants(self):
        """Default variant values for UI tooltips.

        Replacement of `defatults` attribute. Using method gives ability to
        have some "logic" other than attribute values.

        By default returns `default_variants` value.

        Returns:
            list<str>: Whisper variants for user input.
        """
        return copy.deepcopy(self.default_variants)

    def get_default_variant(self):
        """Default variant value that will be used to prefill variant input.

        This is for user input and value may not be content of result from
        `get_default_variants`.

        Can return `None`. In that case first element from
        `get_default_variants` should be used.
        """

        return None

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name
    ):
        return {}

    def get_subset_name(
        self, variant, task_name, asset_doc, project_name, host_name=None
    ):
        """Return subset name for passed context.

        CHANGES:
        Argument `asset_id` was replaced with `asset_doc`. It is easier to
        query asset before. In some cases would this method be called multiple
        times and it would be too slow to query asset document on each
        callback.

        NOTE:
        Asset document is not used yet but is required if would like to use
        task type in subset templates.

        Args:
            variant(str): Subset name variant. In most of cases user input.
            task_name(str): For which task subset is created.
            asset_doc(dict): Asset document for which subset is created.
            project_name(str): Project name.
            host_name(str): Which host creates subset.
        """
        dynamic_data = self.get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name
        )

        return get_subset_name(
            self.family,
            variant,
            task_name,
            asset_doc,
            project_name,
            host_name,
            dynamic_data=dynamic_data
        )

    def get_attribute_defs(self):
        """Plugin attribute definitions.

        Attribute definitions of plugin that hold data about created instance
        and values are stored to metadata for future usage and for publishing
        purposes.

        NOTE:
        Convert method should be implemented which should care about updating
        keys/values when plugin attributes change.

        Returns:
            list<AbtractAttrDef>: Attribute definitions that can be tweaked for
                created instance.
        """
        return []

    def convert_family_attribute_values(self, attribute_values):
        """Convert values loaded from workfile metadata.

        If passed values match current creator version just return the value
        back. Update of changes in workfile must not happen in this method.

        Args:
            attribute_values(dict): Values from instance metadata.

        Returns:
            dict: Converted values.
        """
        return attribute_values


class Creator(BaseCreator):
    """"""
    # Label shown in UI
    label = None

    # Short description of family
    description = None

    @abstractmethod
    def create(self, subset_name, instance_data, options=None):
        """Create new instance and store it.

        Ideally should be stored to workfile using host implementation.

        Args:
            subset_name(str): Subset name of created instance.
            instance_data(dict):
        """

        # instance = AvalonInstance(
        #     self.family, subset_name, instance_data
        # )
        pass

    def get_detail_description(self):
        """Description of family and plugin.

        Can be detailed with html tags.

        Returns:
            str: Detailed description of family for artist. By default returns
                short description.
        """
        return self.description


class AutoCreator(BaseCreator):
    """Creator which is automatically triggered without user interaction.

    Can be used e.g. for `workfile`.
    """
