import os
import pyblish.api
from pymxs import runtime as rt
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.max.api.lib_rendersettings import RenderSettings


class ValidateDeadlinePublish(pyblish.api.InstancePlugin,
                              OptionalPyblishPluginMixin):
    """Validates Render File Directory is
    not the same in every submission
    """

    order = ValidateContentsOrder
    families = ["maxrender"]
    hosts = ["max"]
    label = "Render Output for Deadline"
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        file = rt.maxFileName
        filename, ext = os.path.splitext(file)
        if filename not in rt.rendOutputFilename:
            raise PublishValidationError(
                "Render output folder "
                "doesn't match the max scene name! "
                "Use Repair action to "
                "fix the folder file path.."
            )

    @classmethod
    def repair(cls, instance):
        container = instance.data.get("instance_node")
        RenderSettings().render_output(container)
        cls.log.debug("Reset the render output folder...")
