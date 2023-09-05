import pyblish.api

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateContentsOrder,
)


class ValidateReview(pyblish.api.InstancePlugin, OptionalPyblishPluginMixin):
    """Validate review."""

    order = ValidateContentsOrder
    label = "Validate Review"
    families = ["review"]

    def process(self, instance):
        cameras = instance.data["cameras"]

        # validate required settings
        if len(cameras) == 0:
            raise PublishValidationError(
                "No camera found in review instance: {}".format(instance)
            )
        elif len(cameras) > 2:
            raise PublishValidationError(
                "Only a single camera is allowed for a review instance but "
                "more than one camera found in review instance: {}. "
                "Cameras found: {}".format(instance, ", ".join(cameras))
            )

        self.log.debug('camera: {}'.format(instance.data["review_camera"]))
