import copy
import collections
from uuid import uuid4


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
    def __init__(self, family, subset_name, data=None):

        self.family = family
        self.subset_name = subset_name

        self.data = collections.OrderedDict()
        self.data["id"] = "pyblish.avalon.instance"
        self.data["family"] = family
        self.data["subset"] = subset_name
        self.data["active"] = True
        # Stored family specific attribute values
        # {key: value}
        self.data["family_attributes"] = {}
        # Stored publish specific attribute values
        # {<plugin name>: {key: value}}
        self.data["publish_attributes"] = {}
        if data:
            self.data.update(data)

        if not self.data.get("uuid"):
            self.data["uuid"] = str(uuid4())

    @staticmethod
    def from_existing(instance_data):
        """Convert instance data from workfile to AvalonInstance."""
        instance_data = copy.deepcopy(instance_data)

        family = instance_data.pop("family", None)
        subset_name = instance_data.pop("subset", None)

        return AvalonInstance(family, subset_name, instance_data)


class BaseCreator:
    """Plugin that create and modify instance data before publishing process.

    We should maybe find better name as creation is only one part of it's logic
    and to avoid expectations that it is the same as `avalon.api.Creator`.

    Single object should be used for multiple instances instead of single
    instance per one creator object. Do not store temp data or mid-process data
    to `self` if it's not Plugin specific.
    """
    # Abstract attributes
    # Family that plugin represents
    family = None
    enabled = True

    # GUI Purposes
    # - default_variants may not be used if `get_default_variants` is overriden
    default_variants = []

    def __init__(self, system_settings, project_settings, headless=False):
        # Creator is running in headless mode (without UI elemets)
        # - we may use UI inside processing this attribute should be checked
        self.headless = headless

    def create(self, subset_name, instance_data, options=None):
        """Create new instance in workfile metadata.

        Replacement of `process` method from avalon implementation.
        - must expect all data that were passed to init in previous
            implementation
        """

        # instance = InstanceData(
        #     self.family, subset_name, instance_data
        # )
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
        pass

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
