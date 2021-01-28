from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateCameraContents(pyblish.api.InstancePlugin):
    """Validates Camera instance contents.

    A Camera instance may only hold a SINGLE camera's transform, nothing else.

    It may hold a "locator" as shape, but different shapes are down the
    hierarchy.

    """

    order = pype.api.ValidateContentsOrder
    families = ['camera']
    hosts = ['maya']
    label = 'Camera Contents'
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        # get cameras
        members = instance.data['setMembers']
        shapes = cmds.ls(members, dag=True, shapes=True, long=True)

        # single camera
        invalid = []
        cameras = cmds.ls(shapes, type='camera', long=True)
        if len(cameras) != 1:
            cls.log.warning("Camera instance must have a single camera. "
                            "Found {0}: {1}".format(len(cameras), cameras))
            invalid.extend(cameras)

            # We need to check this edge case because returning an extended
            # list when there are no actual cameras results in
            # still an empty 'invalid' list
            if len(cameras) < 1:
                raise RuntimeError("No cameras in instance.")

        # non-camera shapes
        valid_shapes = cmds.ls(shapes, type=('camera', 'locator'), long=True)
        shapes = set(shapes) - set(valid_shapes)
        if shapes:
            shapes = list(shapes)
            cls.log.warning("Camera instance should only contain camera "
                            "shapes. Found: {0}".format(shapes))
            invalid.extend(shapes)

        invalid = list(set(invalid))

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid camera contents: "
                               "{0}".format(invalid))
