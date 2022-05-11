from openpype.lib import BoolDef
from .lib import load_help_content_from_plugin


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
        self.title = title or "< Missing title >"
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
            list<AbtractAttrDef>: Attribute definitions for plugin.
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

    def get_attr_values_from_data(self, data):
        """Get attribute values for attribute definitions from data.

        Args:
            data(dict): Data from instance or context.
        """
        return (
            data
            .get("publish_attributes", {})
            .get(self.__class__.__name__, {})
        )


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
