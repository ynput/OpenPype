import pyblish.api
from maya import cmds

import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder,
    OptionalPyblishPluginMixin)


class ValidateCameraContents(pyblish.api.InstancePlugin,
                             OptionalPyblishPluginMixin):
    """Validates Camera instance contents.

    A Camera instance may only hold a SINGLE camera's transform, nothing else.

    It may hold a "locator" as shape, but different shapes are down the
    hierarchy.

    """

    order = ValidateContentsOrder
    families = ['camera']
    hosts = ['maya']
    label = 'Camera Contents'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    validate_shapes = True
    optional = False

    @classmethod
    def get_invalid(cls, instance):

        # get cameras
        members = instance.data['setMembers']
        shapes = cmds.ls(members, dag=True, shapes=True, long=True)

        # single camera
        invalid = []
        cameras = cmds.ls(shapes, type='camera', long=True)
        if len(cameras) != 1:
            cls.log.error("Camera instance must have a single camera. "
                          "Found {0}: {1}".format(len(cameras), cameras))
            invalid.extend(cameras)

            # We need to check this edge case because returning an extended
            # list when there are no actual cameras results in
            # still an empty 'invalid' list
            if len(cameras) < 1:
                if members:
                    # If there are members in the instance return all of
                    # them as 'invalid' so the user can still select invalid
                    cls.log.error("No cameras found in instance "
                                  "members: {}".format(members))
                    return members

                raise PublishValidationError(
                    "No cameras found in empty instance.")

        if not cls.validate_shapes:
            cls.log.debug("Not validating shapes in the camera content"
                          " because 'validate shapes' is disabled")
            return invalid

        # non-camera shapes
        valid_shapes = cmds.ls(shapes, type=('camera', 'locator'), long=True)
        shapes = set(shapes) - set(valid_shapes)
        if shapes:
            shapes = list(shapes)
            cls.log.error("Camera instance should only contain camera "
                          "shapes. Found: {0}".format(shapes))
            invalid.extend(shapes)

        invalid = list(set(invalid))
        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Invalid camera contents: "
                               "{0}".format(invalid))
