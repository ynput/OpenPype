import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from maya import cmds
from openpype.pipeline.publish import RepairAction


class ValidateArnoldVerbosityLevel(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """Validate Arnold Verbosity Level For Deadline Submission"""

    order = pyblish.api.ValidatorOrder
    families = ["renderlayer"]
    hosts = ["maya"]
    label = "Validate Arnold Verbosity Level"
    actions = [RepairAction]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        if instance.data["renderer"] != "arnold":
            self.log.debug(
                "The renderer for deadline submission is not Arnold.\n\n"
                " Skipping Validate Arnold Verbosity Level.")
            return
        current_verbosity_level = cmds.getAttr(
            "defaultArnoldRenderOptions.log_verbosity")

        if not current_verbosity_level >= 3:
            report = (
                "Arnold verbosity level has invalid value(s).\n\n"
                "It must be always greater than 3.\n\n"
                "You can use repair action to set the correct value\n"
            )
            raise PublishValidationError(
                report, title="Invalid Value(s) for Arnold Verbosity Level")

    @classmethod
    def repair(cls, instance):
        return cmds.setAttr("defaultArnoldRenderOptions.log_verbosity", 3)
