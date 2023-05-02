import pyblish.api

from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin,
)

from openpype.hosts.fusion.api.action import SelectInvalidAction
from openpype.pipeline.publish import RepairAction

from openpype.hosts.fusion.api.lib import (
    update_frame_range,
    get_comp_render_range,
)


class ValidateFrameRange(
    pyblish.api.InstancePlugin,
    OptionalPyblishPluginMixin,
):
    """Validate if the comp has the correct frame range"""

    order = (
        pyblish.api.ValidatorOrder
    )  # Move the validator so it runs before comp_frame_range
    label = "Validate Frame Range"
    families = ["render"]
    hosts = ["fusion"]
    optional = True
    actions = [SelectInvalidAction, RepairAction]

    @classmethod
    def get_invalid(cls, instance):
        return [instance[0]]

    def process(self, instance):
        # Skip the instance if is not active by data on the instance
        if not self.is_active(instance.data):
            return

        # Get the comps range
        comp = instance.context.data["currentComp"]
        (
            comp_start,
            comp_end,
            comp_global_start,
            comp_global_end,
        ) = get_comp_render_range(comp)

        invalid_reason = []

        if comp_global_start != instance.data["frameStartHandle"]:
            invalid_reason.append(
                '"Global start" is set to {} but should start at {}'.format(
                    int(comp_global_start),
                    instance.data["frameStartHandle"],
                )
            )

        if comp_global_end != instance.data["frameEndHandle"]:
            invalid_reason.append(
                '"Global end" is set to {} but should end at {}'.format(
                    int(comp_global_end),
                    instance.data["frameEndHandle"],
                )
            )

        # render range should start at global start and
        # end at global end to render out the full sequence
        if comp_start != instance.data["frameStartHandle"]:
            invalid_reason.append(
                '"Render start" is set to {} but should start at {}'.format(
                    int(comp_start),
                    instance.data["frameStartHandle"],
                )
            )

        if comp_end != instance.data["frameEndHandle"]:
            invalid_reason.append(
                '"Render end" is set to {} but should end at {}'.format(
                    int(comp_end),
                    instance.data["frameEndHandle"],
                )
            )

        if invalid_reason:
            # Pass instance for "Select invalid" in Publisher
            self.get_invalid(instance)

            # Generate message
            self.log.info(
                '"frame_range_type" is set to "{}"'.format(
                    instance.context.data["frame_range_type"]
                )
            )
            message = ""
            if instance.context.data["frame_range_type"] == "asset_render":
                message = (
                    "The asset's frame range doesn't match the"
                    " current comps's frame range.\n\n\n\n{}"
                ).format("\n\n".join(invalid_reason))
            else:
                message = (
                    'The contexts frame range type is set to "Current frame range".\n\n'
                    'Ether change it to "Asset\'s frame range" or disable'
                    ' "Validate Frame Range" range for this saver."'
                )
            raise PublishValidationError(
                message,
                title=self.label,
            )

    @classmethod
    def repair(cls, instance):
        if instance.context.data["frame_range_type"] == "asset_render":
            update_frame_range(
                instance.data["frameStartHandle"],
                instance.data["frameEndHandle"],
                set_render_range=True,
            )
        else:
            pass
