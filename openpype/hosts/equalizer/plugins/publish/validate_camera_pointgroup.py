import pyblish.api
import tde4

from openpype.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder,
)


class ValidateCameraPoingroup(pyblish.api.InstancePlugin):
    """Validate Camera Point Group.

    There must be a camera point group in the scene.
    """
    order = ValidateContentsOrder
    hosts = ["equalizer"]
    families = ["matchmove"]
    label = "Validate Camera Point Group"

    def process(self, instance):
        valid = False
        for point_group in tde4.getPGroupList():
            if tde4.getPGroupType(point_group) == "CAMERA":
                valid = True
                break

        if not valid:
            raise PublishValidationError("Missing Camera Point Group")
