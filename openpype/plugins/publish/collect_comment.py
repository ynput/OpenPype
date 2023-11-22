"""Collect comment and add option to enter comment per instance.

Combination of plugins. One define optional input for instances in Publisher
UI (CollectInstanceCommentDef) and second cares that each instance during
collection has available "comment" key in data (CollectComment).

Plugin 'CollectInstanceCommentDef' define "comment" attribute which won't be
filled with any value if instance does not match families filter or when
plugin is disabled.

Plugin 'CollectComment' makes sure that each instance in context has
available "comment" key in data which can be set to 'str' or 'None' if is not
set.
- In case instance already has filled comment the plugin's logic is skipped
- The comment is always set and value should be always 'str' even if is empty

Why are separated:
- 'CollectInstanceCommentDef' can have specific settings to show comment
    attribute only to defined families in publisher UI
- 'CollectComment' will run all the time

Todos:
    The comment per instance is not sent via farm.
"""

import pyblish.api
from openpype.lib.attribute_definitions import TextDef
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class CollectInstanceCommentDef(
    pyblish.api.InstancePlugin,
    OpenPypePyblishPluginMixin
):
    label = "Comment per instance"
    targets = ["local"]
    # Disable plugin by default
    families = []
    enabled = False

    def process(self, instance):
        pass

    @classmethod
    def apply_settings(cls, project_setting, _):
        plugin_settings = project_setting["global"]["publish"].get(
            "collect_comment_per_instance"
        )
        if not plugin_settings:
            return

        if plugin_settings.get("enabled") is not None:
            cls.enabled = plugin_settings["enabled"]

        if plugin_settings.get("families") is not None:
            cls.families = plugin_settings["families"]

    @classmethod
    def get_attribute_defs(cls):
        return [
            TextDef("comment", label="Comment")
        ]


class CollectComment(
    pyblish.api.ContextPlugin,
    OpenPypePyblishPluginMixin
):
    """Collect comment per each instance.

    Plugin makes sure each instance to publish has set "comment" in data so any
    further plugin can use it directly.
    """

    label = "Collect Instance Comment"
    # TODO change to CollectorOrder after Pyblish is purged
    # Pyblish allows modifying comment after collect phase
    order = pyblish.api.ExtractorOrder - 0.49

    def process(self, context):
        context_comment = self.cleanup_comment(context.data.get("comment"))
        # Set it back
        context.data["comment"] = context_comment
        for instance in context:
            instance_label = str(instance)
            # Check if comment is already set
            instance_comment = self.cleanup_comment(
                instance.data.get("comment"))

            # If comment on instance is not set then look for attributes
            if not instance_comment:
                attr_values = self.get_attr_values_from_data_for_plugin(
                    CollectInstanceCommentDef, instance.data
                )
                instance_comment = self.cleanup_comment(
                    attr_values.get("comment")
                )

            # Use context comment if instance has all options of comment
            #   empty
            if not instance_comment:
                instance_comment = context_comment

            instance.data["comment"] = instance_comment
            if instance_comment:
                msg_end = "has comment set to: \"{}\"".format(
                    instance_comment)
            else:
                msg_end = "does not have set comment"
            self.log.debug("Instance {} {}".format(instance_label, msg_end))

    def cleanup_comment(self, comment):
        """Cleanup comment value.

        Args:
            comment (Union[str, None]): Comment value from data.

        Returns:
            str: Cleaned comment which is stripped or empty string if input
                was 'None'.
        """

        if comment:
            return comment.strip()
        return ""
