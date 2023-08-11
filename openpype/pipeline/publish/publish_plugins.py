import inspect
from abc import ABCMeta
import pyblish.api
from pyblish.plugin import MetaPlugin, ExplicitMetaPlugin
from openpype.lib.transcoding import VIDEO_EXTENSIONS, IMAGE_EXTENSIONS
from openpype.lib import BoolDef
from openpype.pipeline import expected_files

from .lib import (
    load_help_content_from_plugin,
    get_errored_instances_from_context,
    get_errored_plugins_from_context,
    get_instance_staging_dir,
)

from openpype.pipeline.colorspace import (
    get_colorspace_settings_from_publish_context,
    set_colorspace_data_to_representation
)


class AbstractMetaInstancePlugin(ABCMeta, MetaPlugin):
    pass


class AbstractMetaContextPlugin(ABCMeta, ExplicitMetaPlugin):
    pass


class PublishValidationError(Exception):
    """Validation error happened during publishing.

    This exception should be used when validation publishing failed.

    Has additional UI specific attributes that may be handy for artist.

    Args:
        message(str): Message of error. Short explanation an issue.
        title(str): Title showed in UI. All instances are grouped under
            single title.
        description(str): Detailed description of an error. It is possible
            to use Markdown syntax.
    """

    def __init__(self, message, title=None, description=None, detail=None):
        self.message = message
        self.title = title
        self.description = description or message
        self.detail = detail
        super(PublishValidationError, self).__init__(message)


class PublishXmlValidationError(PublishValidationError):
    def __init__(
        self, plugin, message, key=None, formatting_data=None
    ):
        if key is None:
            key = "main"

        if not formatting_data:
            formatting_data = {}
        result = load_help_content_from_plugin(plugin)
        content_obj = result["errors"][key]
        description = content_obj.description.format(**formatting_data)
        detail = content_obj.detail
        if detail:
            detail = detail.format(**formatting_data)
        super(PublishXmlValidationError, self).__init__(
            message, content_obj.title, description, detail
        )


class KnownPublishError(Exception):
    """Publishing crashed because of known error.

    Message will be shown in UI for artist.
    """

    pass


class OpenPypePyblishPluginMixin:
    # TODO
    # executable_in_thread = False
    #
    # state_message = None
    # state_percent = None
    # _state_change_callbacks = []
    #
    # def set_state(self, percent=None, message=None):
    #     """Inner callback of plugin that would help to show in UI state.
    #
    #     Plugin have registered callbacks on state change which could trigger
    #     update message and percent in UI and repaint the change.
    #
    #     This part must be optional and should not be used to display errors
    #     or for logging.
    #
    #     Message should be short without details.
    #
    #     Args:
    #         percent(int): Percent of processing in range <1-100>.
    #         message(str): Message which will be shown to user (if in UI).
    #     """
    #     if percent is not None:
    #         self.state_percent = percent
    #
    #     if message:
    #         self.state_message = message
    #
    #     for callback in self._state_change_callbacks:
    #         callback(self)

    @classmethod
    def get_attribute_defs(cls):
        """Publish attribute definitions.

        Attributes available for all families in plugin's `families` attribute.
        Returns:
            list<AbstractAttrDef>: Attribute definitions for plugin.
        """

        return []

    @classmethod
    def convert_attribute_values(cls, attribute_values):
        if cls.__name__ not in attribute_values:
            return attribute_values

        plugin_values = attribute_values[cls.__name__]

        attr_defs = cls.get_attribute_defs()
        for attr_def in attr_defs:
            key = attr_def.key
            if key in plugin_values:
                plugin_values[key] = attr_def.convert_value(
                    plugin_values[key]
                )
        return attribute_values

    @staticmethod
    def get_attr_values_from_data_for_plugin(plugin, data):
        """Get attribute values for attribute definitions from data.

        Args:
            plugin (Union[publish.api.Plugin, Type[publish.api.Plugin]]): The
                plugin for which attributes are extracted.
            data(dict): Data from instance or context.
        """

        if not inspect.isclass(plugin):
            plugin = plugin.__class__

        return (
            data
            .get("publish_attributes", {})
            .get(plugin.__name__, {})
        )

    def get_attr_values_from_data(self, data):
        """Get attribute values for attribute definitions from data.

        Args:
            data(dict): Data from instance or context.
        """

        return self.get_attr_values_from_data_for_plugin(self.__class__, data)


class OptionalPyblishPluginMixin(OpenPypePyblishPluginMixin):
    """Prepare mixin for optional plugins.

    Defined active attribute definition prepared for published and
    prepares method which will check if is active or not.

    ```
    class ValidateScene(
        pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
    ):
        def process(self, instance):
            # Skip the instance if is not active by data on the instance
            if not self.is_active(instance.data):
                return
    ```
    """

    @classmethod
    def get_attribute_defs(cls):
        """Attribute definitions based on plugin's optional attribute."""

        # Empty list if plugin is not optional
        if not getattr(cls, "optional", None):
            return []

        # Get active value from class as default value
        active = getattr(cls, "active", True)
        # Return boolean stored under 'active' key with label of the class name
        label = cls.label or cls.__name__
        return [
            BoolDef("active", default=active, label=label)
        ]

    def is_active(self, data):
        """Check if plugins is active for instance/context based on their data.

        Args:
            data(dict): Data from instance or context.
        """
        # Skip if is not optional and return True
        if not getattr(self, "optional", None):
            return True
        attr_values = self.get_attr_values_from_data(data)
        active = attr_values.get("active")
        if active is None:
            active = getattr(self, "active", True)
        return active


class RepairAction(pyblish.api.Action):
    """Repairs the action

    To process the repairing this requires a static `repair(instance)` method
    is available on the plugin.
    """

    label = "Repair"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):
        if not hasattr(plugin, "repair"):
            raise RuntimeError("Plug-in does not have repair method.")

        # Get the errored instances
        self.log.debug("Finding failed instances..")
        errored_instances = get_errored_instances_from_context(context,
                                                               plugin=plugin)
        for instance in errored_instances:
            self.log.debug(
                "Attempting repair for instance: {} ...".format(instance)
            )
            plugin.repair(instance)


class RepairContextAction(pyblish.api.Action):
    """Repairs the action

    To process the repairing this requires a static `repair(context)` method
    is available on the plugin.
    """

    label = "Repair"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):
        if not hasattr(plugin, "repair"):
            raise RuntimeError("Plug-in does not have repair method.")

        # Get the failed instances
        self.log.debug("Finding failed plug-ins..")
        failed_plugins = get_errored_plugins_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        if plugin in failed_plugins:
            self.log.debug("Attempting repair ...")
            plugin.repair(context)


class Extractor(pyblish.api.InstancePlugin):
    """Extractor base class.

    The extractor base class implements a "staging_dir" function used to
    generate a temporary directory for an instance to extract to.

    This temporary directory is generated through `tempfile.mkdtemp()`

    """

    order = 2.0

    def staging_dir(self, instance):
        """Provide a temporary directory in which to store extracted files

        Upon calling this method the staging directory is stored inside
        the instance.data['stagingDir']
        """

        return get_instance_staging_dir(instance)


class ColormanagedPyblishPluginMixin(object):
    """Mixin for colormanaged plugins.

    This class is used to set colorspace data to a publishing
    representation. It contains a static method,
    get_colorspace_settings, which returns config and
    file rules data for the host context.
    It also contains a method, set_representation_colorspace,
    which sets colorspace data to the representation.
    The allowed file extensions are listed in the allowed_ext variable.
    The method first checks if the file extension is in
    the list of allowed extensions. If it is, it then gets the
    colorspace settings from the host context and gets a
    matching colorspace from rules. Finally, it infuses this
    data into the representation.
    """
    allowed_ext = set(
        ext.lstrip(".") for ext in IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)
    )

    def get_colorspace_settings(self, context):
        """[Deprecated] Returns solved settings for the host context.

        Args:
            context (publish.Context): publishing context

        Returns:
            tuple | bool: config, file rules or None
        """
        self.log.warning(
            "'get_colorspace_settings' is deprecated, "
            "use 'get_colorspace_settings_from_publish_context' instead"
        )
        # TODO: for backward compatibility, remove in future
        return get_colorspace_settings_from_publish_context(context.data)

    def set_representation_colorspace(
        self, representation, context,
        colorspace=None,
        colorspace_settings=None
    ):
        """Sets colorspace data to representation.

        Args:
            representation (dict): publishing representation
            context (publish.Context): publishing context
            config_data (dict): host resolved config data
            file_rules (dict): host resolved file rules data
            colorspace (str, optional): colorspace name. Defaults to None.
            colorspace_settings (tuple[dict, dict], optional):
                Settings for config_data and file_rules.
                Defaults to None.

        Example:
            ```
            {
                # for other publish plugins and loaders
                "colorspace": "linear",
                "config": {
                    # for future references in case need
                    "path": "/abs/path/to/config.ocio",
                    # for other plugins within remote publish cases
                    "template": "{project[root]}/path/to/config.ocio"
                }
            }
            ```

        """
        # using cached settings if available
        set_colorspace_data_to_representation(
            representation, context.data,
            colorspace,
            colorspace_settings,
            log=self.log
        )


class FarmPluginMixin:
    """Mixin for farm plugins.

    This mixin provides methods for farm plugins to use.
    """

    def set_expected_files(
        self,
        instance,
        frame_start,
        frame_end,
        path,
        only_existing=False
    ):
        """Create expected files in instance data

        Args:
            instance (pyblish.api.Instance): Instance to set expected files on
            frame_start (int): Start frame of the sequence
            frame_end (int): End frame of the sequence
            path (str): Path to generate expected files from
            only_existing (Optional[bool]): Ensure that files exists.

        Returns:
            None: sets `expectedFiles` key on instance data
        """

        expected_files_list = expected_files.generate_expected_filepaths(
            frame_start, frame_end, path, only_existing)
        instance.data["expectedFiles"] = expected_files_list

    def add_farm_instance_data(self, instance):
        """Add farm publishing related instance data.

        Args:
            instance (pyblish.api.Instance): pyblish instance
        """

        # make sure rendered sequence on farm will
        # be used for extract review
        if not instance.data.get("review"):
            instance.data["useSequenceForReview"] = False

        # Farm rendering
        instance.data.update({
            "transfer": False,
            "farm": True  # to skip integrate
        })
        self.log.info("Farm rendering ON ...")

    def set_farm_representation(
        self,
        instance,
        file_path,
        frame_start=None,
        frame_end=None,
        colorspace=None,
        only_existing=False,
        reviewable=False,
    ):
        """Set farm representation to instance data.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            file_path (str): Path to a single file or a sequence of files
                with a pattern (##, %02d) in it.
            frame_start (Optional[int]): first frame
            frame_end (Optional[int]): last frame
            colorspace (Optional[str]): colorspace name
            only_existing (Optional[bool]): Ensure that files exists.
            reviewable (Optional[bool]): reviewable flag

        Returns:
            dict: representation
        """
        representation = expected_files.get_publishing_representation(
            instance,
            file_path,
            frame_start,
            frame_end,
            colorspace,
            self.log,
            only_existing,
            reviewable,
        )
        representation["tags"].append("publish_on_farm")
        instance.data["representations"].append(representation)

    def set_representation(
        self,
        instance,
        file_path,
        frame_start=None,
        frame_end=None,
        colorspace=None,
        only_existing=False,
        reviewable=False,
    ):
        """Set farm representation to instance data.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            file_path (str): Path to a single file or a sequence of files
                with a pattern (##, %02d) in it.
            frame_start (Optional[int]): first frame
            frame_end (Optional[int]): last frame
            colorspace (Optional[str]): colorspace name
            only_existing (Optional[bool]): Ensure that files exists.
            reviewable (Optional[bool]): reviewable flag

        Returns:
            dict: representation
        """
        representation = expected_files.get_publishing_representation(
            instance,
            file_path,
            frame_start,
            frame_end,
            colorspace,
            self.log,
            only_existing,
            reviewable,
        )
        instance.data["representations"].append(representation)

    def get_single_filepath_from_list_of_files(self, collected_files):
        """Get single filepath from list of files.

        Args:
            collected_files (list[str]): list of files

        Returns:
            Any[str, None]: single filepath or None if not possible
        """
        return expected_files.get_single_filepath_from_list_of_files(
            collected_files)

    def get_frame_range_from_list_of_files(self, collected_files):
        """Get frame range from sequence files.

        Args:
            collected_files (list[str]): list of files

        Returns:
            Any[tuple[int, int], tuple[None, None]]: frame range or None
                if not possible
        """
        return expected_files.get_frame_range_from_list_of_files(
            collected_files)
