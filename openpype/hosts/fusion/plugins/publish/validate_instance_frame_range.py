import pyblish.api

from openpype.pipeline import PublishValidationError


class ValidateInstanceFrameRange(pyblish.api.InstancePlugin):
    """Validate instance frame range is within comp's global render range."""

    order = pyblish.api.ValidatorOrder
    label = "Validate Frame Range"
    families = ["render", "image"]
    hosts = ["fusion"]

    def process(self, instance):

        context = instance.context
        global_start = context.data["compFrameStart"]
        global_end = context.data["compFrameEnd"]

        render_start = instance.data["frameStartHandle"]
        render_end = instance.data["frameEndHandle"]

        if render_start < global_start or render_end > global_end:

            message = (
                f"Instance {instance} render frame range "
                f"({render_start}-{render_end}) is outside of the comp's "
                f"global render range ({global_start}-{global_end}) and thus "
                f"can't be rendered. "
            )
            description = (
                f"{message}\n\n"
                f"Either update the comp's global range or the instance's "
                f"frame range to ensure the comp's frame range includes the "
                f"to render frame range for the instance."
            )
            raise PublishValidationError(
                title="Frame range outside of comp range",
                message=message,
                description=description
            )
