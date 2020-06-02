import re

import pyblish.api
import pype.api
import pype.hosts.maya.action

from maya import cmds


ImagePrefixes = {
    'mentalray': 'defaultRenderGlobals.imageFilePrefix',
    'vray': 'vraySettings.fileNamePrefix',
    'arnold': 'defaultRenderGlobals.imageFilePrefix',
    'renderman': 'defaultRenderGlobals.imageFilePrefix',
    'redshift': 'defaultRenderGlobals.imageFilePrefix'
}


class ValidateRenderSingleCamera(pyblish.api.InstancePlugin):
    """Validate renderable camera count for layer and <Camera> token.

    Pipeline is supporting multiple renderable cameras per layer, but image
    prefix must contain <Camera> token.
    """

    order = pype.api.ValidateContentsOrder
    label = "Render Single Camera"
    hosts = ['maya']
    families = ["renderlayer",
                "vrayscene"]
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    R_CAMERA_TOKEN = re.compile(r'%c|<camera>', re.IGNORECASE)

    def process(self, instance):
        """Process all the cameras in the instance"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid cameras for render.")

    @classmethod
    def get_invalid(cls, instance):

        cameras = instance.data.get("cameras", [])
        renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer').lower()
        # handle various renderman names
        if renderer.startswith('renderman'):
            renderer = 'renderman'
        file_prefix = cmds.getAttr(ImagePrefixes[renderer])

        if len(cameras) > 1:
            if re.search(cls.R_CAMERA_TOKEN, file_prefix):
                # if there is <Camera> token in prefix and we have more then
                # 1 camera, all is ok.
                return
            cls.log.error("Multiple renderable cameras found for %s: %s " %
                          (instance.data["setMembers"], cameras))
            return [instance.data["setMembers"]] + cameras

        elif len(cameras) < 1:
            cls.log.error("No renderable cameras found for %s " %
                          instance.data["setMembers"])
            return [instance.data["setMembers"]]
