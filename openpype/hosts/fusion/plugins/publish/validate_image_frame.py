import pyblish.api

from openpype.pipeline import PublishValidationError


class ValidateImageFrame(pyblish.api.InstancePlugin):
    """Validates that `image` product type contains only single frame."""

    order = pyblish.api.ValidatorOrder
    label = "Validate Image Frame"
    families = [ "image"]
    hosts = ["fusion"]

    def process(self, instance):
        render_start = instance.data["frameStartHandle"]
        render_end = instance.data["frameEndHandle"]
        too_many_frames = (isinstance(instance.data["expectedFiles"], list)
                           and len(instance.data["expectedFiles"]) > 1)

        if render_end - render_start > 0 or too_many_frames:
            desc = "Trying to render {}-{} and expected files: {}.".format(
                render_start, render_end, instance.data["expectedFiles"])
            desc += ("<br><br>Either change frame range based on "
                     "`Frame range source` (eg. asset, node or timeline)"
                     " or use `Render (saver)` creator")
            raise PublishValidationError(
                title="Frame range outside of comp range",
                message=desc,
                description=desc
            )
