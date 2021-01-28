from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateNoDefaultCameras(pyblish.api.InstancePlugin):
    """Ensure no default (startup) cameras are in the instance.

    This might be unnecessary. In the past there were some issues with
    referencing/importing files that contained the start up cameras overriding
    settings when being loaded and sometimes being skipped.
    """

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['camera']
    version = (0, 1, 0)
    label = "No Default Cameras"
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):
        cameras = cmds.ls(instance, type='camera', long=True)
        return [cam for cam in cameras if
                cmds.camera(cam, query=True, startupCamera=True)]

    def process(self, instance):
        """Process all the cameras in the instance"""
        invalid = self.get_invalid(instance)
        assert not invalid, "Default cameras found: {0}".format(invalid)
