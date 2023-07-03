# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidateCameraContent(pyblish.api.InstancePlugin):
    """Validates Camera instance contents.

    A Camera instance may only hold a SINGLE camera's transform
    """

    order = pyblish.api.ValidatorOrder
    families = ["camera"]
    hosts = ["max"]
    label = "Camera Contents"
    camera_type = ["$Free_Camera", "$Target_Camera",
                   "$Physical_Camera", "$Target"]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(("Camera instance must only include"
                                          "camera (and camera target). "
                                          f"Invalid content {invalid}"))

    def get_invalid(self, instance):
        """
        Get invalid nodes if the instance is not camera
        """
        invalid = []
        container = instance.data["instance_node"]
        self.log.info(f"Validating camera content for {container}")

        selection_list = instance.data["members"]
        for sel in selection_list:
            # to avoid Attribute Error from pymxs wrapper
            sel_tmp = str(sel)
            found = any(sel_tmp.startswith(cam) for cam in self.camera_type)
            if not found:
                self.log.error("Camera not found")
                invalid.append(sel)
        return invalid
