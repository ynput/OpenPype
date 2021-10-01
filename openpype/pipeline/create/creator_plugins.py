import copy
import logging

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty
)
import six

from openpype.lib import get_subset_name


class CreatorError(Exception):
    """Should be raised when creator failed because of known issue.

    Message of error should be user readable.
    """

    def __init__(self, message):
        super(CreatorError, self).__init__(message)


class AutoCreationSkipped(Exception):
    """Should be raised when AutoCreator has nothing to do.

    When all instances that would autocreator create already exists.

    Message won't be shown in UI.
    """

    def __init__(self, message):
        self._message = message
        super(AutoCreationSkipped, self).__init__(message)

    def __str__(self):
        return "<{}> {}".format(self.__class__.__name__, self._message)


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

    # Creator (and family) icon
    # - may not be used if `get_icon` is reimplemented
    icon = None

    def __init__(
        self, create_context, system_settings, project_settings, headless=False
    ):
        # Reference to CreateContext
        self.create_context = create_context

        # Creator is running in headless mode (without UI elemets)
        # - we may use UI inside processing this attribute should be checked
        self.headless = headless

    @abstractproperty
    def identifier(self):
        """Family that plugin represents."""
        pass

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

    @abstractmethod
    def collect_instances(self, attr_plugins=None):
        pass

    @abstractmethod
    def update_instances(self, update_list):
        pass

    @abstractmethod
    def remove_instances(self, instances):
        """Method called on instance removement.

        Can also remove instance metadata from context but should return
        'True' if did so.

        Args:
            instance(list<CreatedInstance>): Instance objects which should be
                removed.

        Returns:
            bool: Instance was removed completely and is not required to call
                host's implementation of removement.
        """
        return False

    def get_icon(self):
        """Icon of creator (family).

        Can return path to image file or awesome icon name.
        """
        return self.icon

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

        Default implementation only convert passed values to right types. But
        implementation can be changed to do more stuff (update instance
        to newer version etc.).

        Args:
            attribute_values(dict): Values from instance metadata.

        Returns:
            dict: Converted values.
        """
        attr_defs = self.get_attribute_defs()
        for attr_def in attr_defs:
            key = attr_def.key
            if key in attribute_values:
                attribute_values[key] = attr_def.convert_value(
                    attribute_values[key]
                )
        return attribute_values


class Creator(BaseCreator):
    """Creator that has more information for artist to show in UI.

    Creation requires prepared subset name and instance data.
    """
    # Label shown in UI
    label = None

    # GUI Purposes
    # - default_variants may not be used if `get_default_variants` is overriden
    default_variants = []

    # Short description of family
    # - may not be used if `get_description` is overriden
    description = None

    # Detailed description of family for artists
    # - may not be used if `get_detail_description` is overriden
    detailed_description = None

    @abstractmethod
    def create(self, subset_name, instance_data, options=None):
        """Create new instance and store it.

        Ideally should be stored to workfile using host implementation.

        Args:
            subset_name(str): Subset name of created instance.
            instance_data(dict):
        """

        # instance = CreatedInstance(
        #     self.family, subset_name, instance_data
        # )
        pass

    def get_description(self):
        """Short description of family and plugin.

        Returns:
            str: Short description of family.
        """
        return self.description

    def get_detail_description(self):
        """Description of family and plugin.

        Can be detailed with markdown or html tags.

        Returns:
            str: Detailed description of family for artist.
        """
        return self.detailed_description

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


class AutoCreator(BaseCreator):
    """Creator which is automatically triggered without user interaction.

    Can be used e.g. for `workfile`.
    """
    def remove_instances(self, instances):
        """Skip removement."""
        pass
