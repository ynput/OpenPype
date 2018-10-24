from maya import cmds

import pyblish.api
import pype.api
import pype.maya.action
import pype.maya.lib as lib


class ValidateRenderNoDefaultCameras(pyblish.api.InstancePlugin):
    """Ensure no default (startup) cameras are to be rendered."""

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ["renderlayer']
    label = "No Default Cameras Renderable"
    actions = [pype.maya.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        layer = instance.data["setMembers"]

        # Collect default cameras
        cameras = cmds.ls(type='camera', long=True)
        defaults = [cam for cam in cameras if
                    cmds.camera(cam, query=True, startupCamera=True)]

        invalid = []
        with lib.renderlayer(layer):
            for cam in defaults:
                if cmds.getAttr(cam + ".renderable"):
                    invalid.append(cam)

        return invalid

    def process(self, instance):
        """Process all the cameras in the instance"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Renderable default cameras "
                               "found: {0}".format(invalid))
