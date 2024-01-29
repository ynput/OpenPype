import pyblish.api
from openpype.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin,
)
from openpype.hosts.tvpaint.api.lib import execute_george


class RepairStartFrame(pyblish.api.Action):
    """Repair start frame."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        execute_george(f"tv_startframe {plugin.start_frame}")


class ValidateStartFrame(
    OptionalPyblishPluginMixin,
    pyblish.api.ContextPlugin
):
    """Validate start frame being at frame 0."""

    label = "Validate Start Frame"
    order = pyblish.api.ValidatorOrder
    hosts = ["tvpaint"]
    actions = [RepairStartFrame]
    optional = True
    start_frame = 0

    def process(self, context):
        if not self.is_active(context.data):
            return

        scene_start_frame = execute_george("tv_startframe")
        if scene_start_frame == self.start_frame:
            return

        raise PublishXmlValidationError(
            self,
            f"Start frame has to be frame {self.start_frame}.",
            formatting_data={
                "start_frame_expected": self.start_frame,
                "current_start_frame": scene_start_frame
            }
        )
