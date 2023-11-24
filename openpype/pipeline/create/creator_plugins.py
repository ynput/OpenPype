# -*- coding: utf-8 -*-
import copy
import collections

from abc import ABCMeta, abstractmethod

import six

from openpype.settings import get_system_settings, get_project_settings
from openpype.lib import Logger, is_func_signature_supported
from openpype.pipeline.plugin_discover import (
    discover,
    register_plugin,
    register_plugin_path,
    deregister_plugin,
    deregister_plugin_path
)

from .constants import DEFAULT_VARIANT_VALUE
from .subset_name import get_subset_name
from .utils import get_next_versions_for_instances
from .legacy_create import LegacyCreator


class CreatorError(Exception):
    """Should be raised when creator failed because of known issue.

    Message of error should be user readable.
    """

    def __init__(self, message):
        super(CreatorError, self).__init__(message)


@six.add_metaclass(ABCMeta)
class SubsetConvertorPlugin(object):
    """Helper for conversion of instances created using legacy creators.

    Conversion from legacy creators would mean to loose legacy instances,
    convert them automatically or write a script which must user run. All of
    these solutions are workign but will happen without asking or user must
    know about them. This plugin can be used to show legacy instances in
    Publisher and give user ability to run conversion script.

    Convertor logic should be very simple. Method 'find_instances' is to
    look for legacy instances in scene a possibly call
    pre-implemented 'add_convertor_item'.

    User will have ability to trigger conversion which is executed by calling
    'convert' which should call 'remove_convertor_item' when is done.

    It does make sense to add only one or none legacy item to create context
    for convertor as it's not possible to choose which instace are converted
    and which are not.

    Convertor can use 'collection_shared_data' property like creators. Also
    can store any information to it's object for conversion purposes.

    Args:
        create_context
    """

    _log = None

    def __init__(self, create_context):
        self._create_context = create_context

    @property
    def log(self):
        """Logger of the plugin.

        Returns:
            logging.Logger: Logger with name of the plugin.
        """

        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    @property
    def host(self):
        return self._create_context.host

    @property
    @abstractmethod
    def identifier(self):
        """Converted identifier.

        Returns:
            str: Converted identifier unique for all converters in host.
        """

        pass

    @abstractmethod
    def find_instances(self):
        """Look for legacy instances in the scene.

        Should call 'add_convertor_item' if there is at least one instance to
        convert.
        """

        pass

    @abstractmethod
    def convert(self):
        """Conversion code."""

        pass

    @property
    def create_context(self):
        """Quick access to create context.

        Returns:
            CreateContext: Context which initialized the plugin.
        """

        return self._create_context

    @property
    def collection_shared_data(self):
        """Access to shared data that can be used during 'find_instances'.

        Retruns:
            Dict[str, Any]: Shared data.

        Raises:
            UnavailableSharedData: When called out of collection phase.
        """

        return self._create_context.collection_shared_data

    def add_convertor_item(self, label):
        """Add item to CreateContext.

        Args:
            label (str): Label of item which will show in UI.
        """

        self._create_context.add_convertor_item(self.identifier, label)

    def remove_convertor_item(self):
        """Remove legacy item from create context when conversion finished."""

        self._create_context.remove_convertor_item(self.identifier)


@six.add_metaclass(ABCMeta)
class BaseCreator:
    """Plugin that create and modify instance data before publishing process.

    We should maybe find better name as creation is only one part of it's logic
    and to avoid expectations that it is the same as `avalon.api.Creator`.

    Single object should be used for multiple instances instead of single
    instance per one creator object. Do not store temp data or mid-process data
    to `self` if it's not Plugin specific.

    Args:
        project_settings (Dict[str, Any]): Project settings.
        create_context (CreateContext): Context which initialized creator.
        headless (bool): Running in headless mode.
    """

    # Label shown in UI
    label = None
    group_label = None
    # Cached group label after first call 'get_group_label'
    _cached_group_label = None

    # Order in which will be plugin executed (collect & update instances)
    #   less == earlier -> Order '90' will be processed before '100'
    order = 100

    # Variable to store logger
    _log = None

    # Creator is enabled (Probably does not have reason of existence?)
    enabled = True

    # Creator (and family) icon
    # - may not be used if `get_icon` is reimplemented
    icon = None

    # Instance attribute definitions that can be changed per instance
    # - returns list of attribute definitions from
    #       `openpype.pipeline.attribute_definitions`
    instance_attr_defs = []

    # Filtering by host name - can be used to be filtered by host name
    # - used on all hosts when set to 'None' for Backwards compatibility
    #   - was added afterwards
    # QUESTION make this required?
    host_name = None

    # Settings auto-apply helpers
    # Root key in project settings (mandatory for auto-apply to work)
    settings_category = None
    # Name of plugin in create settings > class name is used if not set
    settings_name = None

    def __init__(
        self, project_settings, system_settings, create_context, headless=False
    ):
        # Reference to CreateContext
        self.create_context = create_context
        self.project_settings = project_settings

        # Creator is running in headless mode (without UI elemets)
        # - we may use UI inside processing this attribute should be checked
        self.headless = headless

        expect_system_settings = False
        if is_func_signature_supported(
            self.apply_settings, project_settings
        ):
            self.apply_settings(project_settings)
        else:
            expect_system_settings = True
            # Backwards compatibility for system settings
            self.apply_settings(project_settings, system_settings)

        init_use_base = any(
            self.__class__.__init__ is cls.__init__
            for cls in {
                BaseCreator,
                Creator,
                HiddenCreator,
                AutoCreator,
            }
        )
        if not init_use_base or expect_system_settings:
            self.log.warning((
                "WARNING: Source - Create plugin {}."
                " System settings argument will not be passed to"
                " '__init__' and 'apply_settings' methods in future versions"
                " of OpenPype. Planned version to drop the support"
                " is 3.16.6 or 3.17.0. Please contact Ynput core team if you"
                " need to keep system settings."
            ).format(self.__class__.__name__))

    @staticmethod
    def _get_settings_values(project_settings, category_name, plugin_name):
        """Helper method to get settings values.

        Args:
            project_settings (dict[str, Any]): Project settings.
            category_name (str): Category of settings.
            plugin_name (str): Name of settings.

        Returns:
            Union[dict[str, Any], None]: Settings values or None.
        """

        settings = project_settings.get(category_name)
        if not settings:
            return None

        create_settings = settings.get("create")
        if not create_settings:
            return None

        return create_settings.get(plugin_name)

    def apply_settings(self, project_settings):
        """Method called on initialization of plugin to apply settings.

        Default implementation tries to auto-apply settings values if are
            in expected hierarchy.

        Data hierarchy to auto-apply settings:
            ├─ {self.settings_category}                 - Root key in settings
            │ └─ "create"                               - Hardcoded key
            │   └─ {self.settings_name} | {class name}  - Name of plugin
            │     ├─ ... attribute values...            - Attribute/value pair

        It is mandatory to define 'settings_category' attribute. Attribute
        'settings_name' is optional and class name is used if is not defined.

        Example data:
            ProjectSettings {
                "maya": {                    # self.settings_category
                    "create": {              # Hardcoded key
                        "CreateAnimation": { # self.settings_name / class name
                            "enabled": True, # --- Attributes to set ---
                            "optional": True,#
                            "active": True,  #
                            "fps": 25,       # -------------------------
                        },
                        ...
                    },
                    ...
                },
                ...
            }

        Args:
            project_settings (dict[str, Any]): Project settings.
        """

        settings_category = self.settings_category
        if not settings_category:
            return

        cls_name = self.__class__.__name__
        settings_name = self.settings_name or cls_name

        settings = self._get_settings_values(
            project_settings, settings_category, settings_name
        )
        if settings is None:
            self.log.debug("No settings found for {}".format(cls_name))
            return

        for key, value in settings.items():
            # Log out attributes that are not defined on plugin object
            # - those may be potential dangerous typos in settings
            if not hasattr(self, key):
                self.log.debug((
                    "Applying settings to unknown attribute '{}' on '{}'."
                ).format(
                    key, cls_name
                ))
            setattr(self, key, value)


    @property
    def identifier(self):
        """Identifier of creator (must be unique).

        Default implementation returns plugin's family.
        """

        return self.family

    @property
    @abstractmethod
    def family(self):
        """Family that plugin represents."""

        pass

    @property
    def project_name(self):
        """Current project name.

        Returns:
            str: Name of a project.
        """

        return self.create_context.project_name

    @property
    def project_anatomy(self):
        """Current project anatomy.

        Returns:
            Anatomy: Project anatomy object.
        """

        return self.create_context.project_anatomy

    @property
    def host(self):
        return self.create_context.host

    def get_group_label(self):
        """Group label under which are instances grouped in UI.

        Default implementation use attributes in this order:
            - 'group_label' -> 'label' -> 'identifier'
                Keep in mind that 'identifier' use 'family' by default.

        Returns:
            str: Group label that can be used for grouping of instances in UI.
                Group label can be overriden by instance itself.
        """

        if self._cached_group_label is None:
            label = self.identifier
            if self.group_label:
                label = self.group_label
            elif self.label:
                label = self.label
            self._cached_group_label = label
        return self._cached_group_label

    @property
    def log(self):
        """Logger of the plugin.

        Returns:
            logging.Logger: Logger with name of the plugin.
        """

        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def _add_instance_to_context(self, instance):
        """Helper method to add instance to create context.

        Instances should be stored to DCC workfile metadata to be able reload
        them and also stored to CreateContext in which is creator plugin
        existing at the moment to be able use it without refresh of
        CreateContext.

        Args:
            instance (CreatedInstance): New created instance.
        """

        self.create_context.creator_adds_instance(instance)

    def _remove_instance_from_context(self, instance):
        """Helper method to remove instance from create context.

        Instances must be removed from DCC workfile metadat aand from create
        context in which plugin is existing at the moment of removement to
        propagate the change without restarting create context.

        Args:
            instance (CreatedInstance): Instance which should be removed.
        """

        self.create_context.creator_removed_instance(instance)

    @abstractmethod
    def create(self):
        """Create new instance.

        Replacement of `process` method from avalon implementation.
        - must expect all data that were passed to init in previous
            implementation
        """

        pass

    @abstractmethod
    def collect_instances(self):
        """Collect existing instances related to this creator plugin.

        The implementation differs on host abilities. The creator has to
        collect metadata about instance and create 'CreatedInstance' object
        which should be added to 'CreateContext'.

        Example:
        ```python
        def collect_instances(self):
            # Getting existing instances is different per host implementation
            for instance_data in pipeline.list_instances():
                # Process only instances that were created by this creator
                creator_id = instance_data.get("creator_identifier")
                if creator_id == self.identifier:
                    # Create instance object from existing data
                    instance = CreatedInstance.from_existing(
                        instance_data, self
                    )
                    # Add instance to create context
                    self._add_instance_to_context(instance)
        ```
        """

        pass

    @abstractmethod
    def update_instances(self, update_list):
        """Store changes of existing instances so they can be recollected.

        Args:
            update_list(List[UpdateData]): Gets list of tuples. Each item
                contain changed instance and it's changes.
        """

        pass

    @abstractmethod
    def remove_instances(self, instances):
        """Method called on instance removement.

        Can also remove instance metadata from context but should return
        'True' if did so.

        Args:
            instance(List[CreatedInstance]): Instance objects which should be
                removed.
        """

        pass

    def get_icon(self):
        """Icon of creator (family).

        Can return path to image file or awesome icon name.
        """

        return self.icon

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        """Dynamic data for subset name filling.

        These may be get dynamically created based on current context of
        workfile.
        """

        return {}

    def get_subset_name(
        self,
        variant,
        task_name,
        asset_doc,
        project_name,
        host_name=None,
        instance=None
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

        Method is also called on subset name update. In that case origin
        instance is passed in.

        Args:
            variant(str): Subset name variant. In most of cases user input.
            task_name(str): For which task subset is created.
            asset_doc(dict): Asset document for which subset is created.
            project_name(str): Project name.
            host_name(str): Which host creates subset.
            instance(CreatedInstance|None): Object of 'CreatedInstance' for
                which is subset name updated. Passed only on subset name
                update.
        """

        dynamic_data = self.get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )

        return get_subset_name(
            self.family,
            variant,
            task_name,
            asset_doc,
            project_name,
            host_name,
            dynamic_data=dynamic_data,
            project_settings=self.project_settings
        )

    def get_instance_attr_defs(self):
        """Plugin attribute definitions.

        Attribute definitions of plugin that hold data about created instance
        and values are stored to metadata for future usage and for publishing
        purposes.

        NOTE:
        Convert method should be implemented which should care about updating
        keys/values when plugin attributes change.

        Returns:
            List[AbstractAttrDef]: Attribute definitions that can be tweaked
                for created instance.
        """

        return self.instance_attr_defs

    @property
    def collection_shared_data(self):
        """Access to shared data that can be used during creator's collection.

        Retruns:
            Dict[str, Any]: Shared data.

        Raises:
            UnavailableSharedData: When called out of collection phase.
        """

        return self.create_context.collection_shared_data

    def set_instance_thumbnail_path(self, instance_id, thumbnail_path=None):
        """Set path to thumbnail for instance."""

        self.create_context.thumbnail_paths_by_instance_id[instance_id] = (
            thumbnail_path
        )

    def get_next_versions_for_instances(self, instances):
        """Prepare next versions for instances.

        This is helper method to receive next possible versions for instances.
        It is using context information on instance to receive them, 'asset'
        and 'subset'.

        Output will contain version by each instance id.

        Args:
            instances (list[CreatedInstance]): Instances for which to get next
                versions.

        Returns:
            Dict[str, int]: Next versions by instance id.
        """

        return get_next_versions_for_instances(
            self.create_context.project_name, instances
        )


class Creator(BaseCreator):
    """Creator that has more information for artist to show in UI.

    Creation requires prepared subset name and instance data.
    """

    # GUI Purposes
    # - default_variants may not be used if `get_default_variants` is overriden
    default_variants = []

    # Default variant used in 'get_default_variant'
    _default_variant = None

    # Short description of family
    # - may not be used if `get_description` is overriden
    description = None

    # Detailed description of family for artists
    # - may not be used if `get_detail_description` is overriden
    detailed_description = None

    # It does make sense to change context on creation
    # - in some cases it may confuse artists because it would not be used
    #      e.g. for buld creators
    create_allow_context_change = True
    # A thumbnail can be passed in precreate attributes
    # - if is set to True is should expect that a thumbnail path under key
    #   PRE_CREATE_THUMBNAIL_KEY can be sent in data with precreate data
    # - is disabled by default because the feature was added in later stages
    #   and creators who would not expect PRE_CREATE_THUMBNAIL_KEY could
    #   cause issues with instance data
    create_allow_thumbnail = False

    # Precreate attribute definitions showed before creation
    # - similar to instance attribute definitions
    pre_create_attr_defs = []

    def __init__(self, *args, **kwargs):
        cls = self.__class__

        # Fix backwards compatibility for plugins which override
        #   'default_variant' attribute directly
        if not isinstance(cls.default_variant, property):
            # Move value from 'default_variant' to '_default_variant'
            self._default_variant = self.default_variant
            # Create property 'default_variant' on the class
            cls.default_variant = property(
                cls._get_default_variant_wrap,
                cls._set_default_variant_wrap
            )
        super(Creator, self).__init__(*args, **kwargs)

    @property
    def show_order(self):
        """Order in which is creator shown in UI.

        Returns:
            int: Order in which is creator shown (less == earlier). By default
                is using Creator's 'order' or processing.
        """

        return self.order

    @abstractmethod
    def create(self, subset_name, instance_data, pre_create_data):
        """Create new instance and store it.

        Ideally should be stored to workfile using host implementation.

        Args:
            subset_name(str): Subset name of created instance.
            instance_data(dict): Base data for instance.
            pre_create_data(dict): Data based on pre creation attributes.
                Those may affect how creator works.
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

        Replacement of `default_variants` attribute. Using method gives
        ability to have some "logic" other than attribute values.

        By default, returns `default_variants` value.

        Returns:
            List[str]: Whisper variants for user input.
        """

        return copy.deepcopy(self.default_variants)

    def get_default_variant(self, only_explicit=False):
        """Default variant value that will be used to prefill variant input.

        This is for user input and value may not be content of result from
        `get_default_variants`.

        Note:
            This method does not allow to have empty string as
                default variant.

        Args:
            only_explicit (Optional[bool]): If True, only explicit default
                variant from '_default_variant' will be returned.

        Returns:
            str: Variant value.
        """

        if only_explicit or self._default_variant:
            return self._default_variant

        for variant in self.get_default_variants():
            return variant
        return DEFAULT_VARIANT_VALUE

    def _get_default_variant_wrap(self):
        """Default variant value that will be used to prefill variant input.

        Wrapper for 'get_default_variant'.

        Notes:
            This method is wrapper for 'get_default_variant'
                for 'default_variant' property, so creator can override
                the method.

        Returns:
            str: Variant value.
        """

        return self.get_default_variant()

    def _set_default_variant_wrap(self, variant):
        """Set default variant value.

        This method is needed for automated settings overrides which are
        changing attributes based on keys in settings.

        Args:
            variant (str): New default variant value.
        """

        self._default_variant = variant

    default_variant = property(
        _get_default_variant_wrap,
        _set_default_variant_wrap
    )

    def get_pre_create_attr_defs(self):
        """Plugin attribute definitions needed for creation.
        Attribute definitions of plugin that define how creation will work.
        Values of these definitions are passed to `create` method.

        Note:
            Convert method should be implemented which should care about
            updating keys/values when plugin attributes change.

        Returns:
            List[AbstractAttrDef]: Attribute definitions that can be tweaked
                for created instance.
        """
        return self.pre_create_attr_defs


class HiddenCreator(BaseCreator):
    @abstractmethod
    def create(self, instance_data, source_data):
        pass


class AutoCreator(BaseCreator):
    """Creator which is automatically triggered without user interaction.

    Can be used e.g. for `workfile`.
    """

    def remove_instances(self, instances):
        """Skip removement."""
        pass


def discover_creator_plugins(*args, **kwargs):
    return discover(BaseCreator, *args, **kwargs)


def discover_convertor_plugins(*args, **kwargs):
    return discover(SubsetConvertorPlugin, *args, **kwargs)


def discover_legacy_creator_plugins():
    from openpype.pipeline import get_current_project_name

    log = Logger.get_logger("CreatorDiscover")

    plugins = discover(LegacyCreator)
    project_name = get_current_project_name()
    system_settings = get_system_settings()
    project_settings = get_project_settings(project_name)
    for plugin in plugins:
        try:
            plugin.apply_settings(project_settings, system_settings)
        except Exception:
            log.warning(
                "Failed to apply settings to creator {}".format(
                    plugin.__name__
                ),
                exc_info=True
            )
    return plugins


def get_legacy_creator_by_name(creator_name, case_sensitive=False):
    """Find creator plugin by name.

    Args:
        creator_name (str): Name of creator class that should be returned.
        case_sensitive (bool): Match of creator plugin name is case sensitive.
            Set to `False` by default.

    Returns:
        Creator: Return first matching plugin or `None`.
    """

    # Lower input creator name if is not case sensitive
    if not case_sensitive:
        creator_name = creator_name.lower()

    for creator_plugin in discover_legacy_creator_plugins():
        _creator_name = creator_plugin.__name__

        # Lower creator plugin name if is not case sensitive
        if not case_sensitive:
            _creator_name = _creator_name.lower()

        if _creator_name == creator_name:
            return creator_plugin
    return None


def register_creator_plugin(plugin):
    if issubclass(plugin, BaseCreator):
        register_plugin(BaseCreator, plugin)

    elif issubclass(plugin, LegacyCreator):
        register_plugin(LegacyCreator, plugin)

    elif issubclass(plugin, SubsetConvertorPlugin):
        register_plugin(SubsetConvertorPlugin, plugin)


def deregister_creator_plugin(plugin):
    if issubclass(plugin, BaseCreator):
        deregister_plugin(BaseCreator, plugin)

    elif issubclass(plugin, LegacyCreator):
        deregister_plugin(LegacyCreator, plugin)

    elif issubclass(plugin, SubsetConvertorPlugin):
        deregister_plugin(SubsetConvertorPlugin, plugin)


def register_creator_plugin_path(path):
    register_plugin_path(BaseCreator, path)
    register_plugin_path(LegacyCreator, path)
    register_plugin_path(SubsetConvertorPlugin, path)


def deregister_creator_plugin_path(path):
    deregister_plugin_path(BaseCreator, path)
    deregister_plugin_path(LegacyCreator, path)
    deregister_plugin_path(SubsetConvertorPlugin, path)


def cache_and_get_instances(creator, shared_key, list_instances_func):
    """Common approach to cache instances in shared data.

    This is helper function which does not handle cases when a 'shared_key' is
    used for different list instances functions. The same approach of caching
    instances into 'collection_shared_data' is not required but is so common
    we've decided to unify it to some degree.

    Function 'list_instances_func' is called only if 'shared_key' is not
    available in 'collection_shared_data' on creator.

    Args:
        creator (Creator): Plugin which would like to get instance data.
        shared_key (str): Key under which output of function will be stored.
        list_instances_func (Function): Function that will return instance data
            if data were not yet stored under 'shared_key'.

    Returns:
        Dict[str, Dict[str, Any]]: Cached instances by creator identifier from
            result of passed function.
    """

    if shared_key not in creator.collection_shared_data:
        value = collections.defaultdict(list)
        for instance in list_instances_func():
            identifier = instance.get("creator_identifier")
            value[identifier].append(instance)
        creator.collection_shared_data[shared_key] = value
    return creator.collection_shared_data[shared_key]
