import pyblish.api

from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin,
)
from openpype.pipeline.publish import RepairContextAction

from openpype.pipeline.context_tools import get_current_project_asset
from openpype.hosts.fusion.api.lib import (
    set_asset_framerange,
)


class ValidateFrameRange(
    pyblish.api.ContextPlugin,
    OptionalPyblishPluginMixin,
):
    """Validate if the comp has the correct frame range"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Frame Range"
    families = ["render"]
    hosts = ["fusion"]
    optional = True
    actions = [RepairContextAction]

    def process(self, context):
        if not self.is_active(context.data):
            return

        asset_doc = get_current_project_asset()
        start = asset_doc["data"]["frameStart"]
        end = asset_doc["data"]["frameEnd"]
        handle_start = asset_doc["data"]["handleStart"]
        handle_end = asset_doc["data"]["handleEnd"]

        # Convert any potential none type to zero
        handle_start = handle_start or 0
        handle_end = handle_end or 0

        # Calcualte in/out points
        range_start = start - handle_start
        range_end = end - handle_start

        invalid = self.get_invalid(context, range_start, range_end)
        if invalid:
            raise PublishValidationError(
                "The comp's frame range isn't correct"
                "compared to the asset's properties."
                "\n\n{}".format("\n\n".join(invalid)),
                title=self.label,
            )

    @classmethod
    def get_invalid(cls, context, range_start, range_end):
        invalid = []

        if range_start != context.data["frameStartHandle"]:
            invalid.append(
                '"Globla start frame" is set to {} but should start at {}'.format(
                    context.data["frameStartHandle"],
                    range_start,
                )
            )

        if range_end != context.data["frameEndHandle"]:
            invalid.append(
                '"Globla end frame" is set to {} but should end at {}'.format(
                    context.data["frameEndHandle"],
                    range_end,
                )
            )

        return invalid

    @classmethod
    def repair(cls, context):
        set_asset_framerange()
