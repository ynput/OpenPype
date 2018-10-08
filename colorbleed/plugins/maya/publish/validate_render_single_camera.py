from maya import cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.action
import colorbleed.maya.lib as lib


class ValidateRenderSingleCamera(pyblish.api.InstancePlugin):
    """Only one camera may be renderable in a layer.

    Currently the pipeline supports only a single camera per layer.
    This is because when multiple cameras are rendered the output files
    automatically get different names because the <Camera> render token
    is not in the output path. As such the output files conflict with how
    our pipeline expects the output.

    """

    order = colorbleed.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['colorbleed.renderlayer']
    label = "Render Single Camera"
    actions = [colorbleed.maya.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        layer = instance.data["setMembers"]

        cameras = cmds.ls(type='camera', long=True)

        with lib.renderlayer(layer):
            renderable = [cam for cam in cameras if
                          cmds.getAttr(cam + ".renderable")]

            if len(renderable) == 0:
                raise RuntimeError("No renderable cameras found.")
            elif len(renderable) > 1:
                return renderable
            else:
                return []

    def process(self, instance):
        """Process all the cameras in the instance"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Multiple renderable cameras"
                               "found: {0}".format(invalid))
