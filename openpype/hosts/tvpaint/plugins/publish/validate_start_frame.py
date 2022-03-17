import pyblish.api
from openpype.pipeline import PublishXmlValidationError
from openpype.hosts.tvpaint.api import lib


class RepairStartFrame(pyblish.api.Action):
    """Repair start frame."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        lib.execute_george("tv_startframe 0")


class ValidateStartFrame(pyblish.api.ContextPlugin):
    """Validate start frame being at frame 0."""

    label = "Validate Start Frame"
    order = pyblish.api.ValidatorOrder
    hosts = ["tvpaint"]
    actions = [RepairStartFrame]
    optional = True

    def process(self, context):
        start_frame = lib.execute_george("tv_startframe")
        if start_frame == 0:
            return

        raise PublishXmlValidationError(
            self,
            "Start frame has to be frame 0.",
            formatting_data={
                "current_start_frame": start_frame
            }
        )
