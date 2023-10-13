# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateInstanceHasMembers(pyblish.api.InstancePlugin):
    """Validates Instance has members.

    Check if MaxScene containers includes any contents underneath.
    """

    order = pyblish.api.ValidatorOrder
    families = ["camera",
                "model",
                "maxScene",
                "review",
                "pointcache",
                "pointcloud",
                "redshiftproxy"]
    hosts = ["max"]
    label = "Container Contents"

    def process(self, instance):
        if not instance.data["members"]:
            raise PublishValidationError("No content found in the container")
