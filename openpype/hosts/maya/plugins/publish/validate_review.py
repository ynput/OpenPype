from maya import cmds

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder, PublishValidationError
)


class ValidateReview(pyblish.api.InstancePlugin):
    """Validate review."""

    order = ValidateContentsOrder
    label = "Validate Review"
    families = ["review"]

    def process(self, instance):
        cameras = cmds.ls(
            instance.data["setMembers"], long=True, dag=True, cameras=True
        )

        if len(cameras) != 1:
            raise PublishValidationError(
                "Not a single camera found in instance."
            )
