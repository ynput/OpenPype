import pyblish.api
import bpy

import openpype.hosts.blender.api.action
from openpype.pipeline.publish import (
    PublishValidationError, ValidateContentsOrder)


class ValidateCameraContents(pyblish.api.InstancePlugin):
    """Validates Camera instance contents.

    A Camera instance may only hold a SINGLE camera, nothing else.
    """

    order = ValidateContentsOrder
    families = ['camera']
    hosts = ['blender']
    label = 'Validate Camera Contents'
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        # get cameras
        cameras = [obj for obj in instance if obj.type == "CAMERA"]

        invalid = []
        if len(cameras) != 1:
            invalid.extend(cameras)

        invalid = list(set(invalid))
        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid camera contents, Camera instance must have a single camera: "
                               "Found {0}: {1}".format(len(invalid), invalid))
