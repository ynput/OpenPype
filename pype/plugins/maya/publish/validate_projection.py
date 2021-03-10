import pyblish.api

import pype.api


class ValidateProjection(pyblish.api.InstancePlugin):
    """Validate projection data content."""

    order = pype.api.ValidateContentsOrder
    label = "Projection"
    hosts = ["maya"]
    families = ["projection"]

    def process(self, instance):
        cameras = instance.data["cameras"]
        msg = (
            "Only one camera per projection subset is supported."
            "\nCameras found: {}".format([x.name() for x in cameras])
        )
        assert len(cameras) == 1, msg
