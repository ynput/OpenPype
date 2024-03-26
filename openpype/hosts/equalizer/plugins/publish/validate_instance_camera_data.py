import pyblish.api

from openpype.pipeline import PublishValidationError
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateInstanceCameraData(pyblish.api.InstancePlugin):
    """Check if instance has camera data.

    There might not be any camera associated with the instance
    and without it, the instance is not valid.
    """

    order = ValidateContentsOrder
    hosts = ["equalizer"]
    families = ["matchmove"]
    label = "Validate Instance has Camera data"

    def process(self, instance):
        try:
            _ = instance.data["cameras"]
        except KeyError as e:
            raise PublishValidationError("No camera data found") from e
