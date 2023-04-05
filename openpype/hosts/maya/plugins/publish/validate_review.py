from maya import cmds

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder, KnownPublishError
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

        # validate required settings
        if len(cameras) == 0:
            raise KnownPublishError(
                "No camera found in review instance: {}".format(instance)
            )
        elif len(cameras) > 2:
            raise KnownPublishError(
                "Only a single camera is allowed for a review instance but "
                "more than one camera found in review instance: {}. "
                "Cameras found: {}".format(instance, ", ".join(cameras))
            )

        camera = cameras[0]
        self.log.debug('camera: {}'.format(camera))
