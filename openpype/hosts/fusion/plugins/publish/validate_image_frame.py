import pyblish.api

from openpype.pipeline import PublishValidationError


class ValidateImageFrame(pyblish.api.InstancePlugin):
    """Validates that `image` product type contains only single frame."""

    order = pyblish.api.ValidatorOrder
    label = "Validate Image Frame"
    families = ["image"]
    hosts = ["fusion"]

    def process(self, instance):
        render_start = instance.data["frameStartHandle"]
        render_end = instance.data["frameEndHandle"]
        too_many_frames = (isinstance(instance.data["expectedFiles"], list)
                           and len(instance.data["expectedFiles"]) > 1)

        if render_end - render_start > 0 or too_many_frames:
            desc = ("Trying to render multiple frames. 'image' product type "
                    "is meant for single frame. Please use 'render' creator.")
            raise PublishValidationError(
                title="Frame range outside of comp range",
                message=desc,
                description=desc
            )
