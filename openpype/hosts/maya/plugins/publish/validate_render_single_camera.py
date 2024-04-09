import re

import pyblish.api
from maya import cmds

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api.lib_rendersettings import RenderSettings
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateRenderSingleCamera(pyblish.api.InstancePlugin,
                                 OptionalPyblishPluginMixin):
    """Validate renderable camera count for layer and <Camera> token.

    Pipeline is supporting multiple renderable cameras per layer, but image
    prefix must contain <Camera> token.
    """

    order = ValidateContentsOrder
    label = "Render Single Camera"
    hosts = ['maya']
    families = ["renderlayer",
                "vrayscene"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = False

    R_CAMERA_TOKEN = re.compile(r'%c|<camera>', re.IGNORECASE)

    def process(self, instance):
        """Process all the cameras in the instance"""
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Invalid cameras for render.")

    @classmethod
    def get_invalid(cls, instance):

        cameras = instance.data.get("cameras", [])
        renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer').lower()
        # handle various renderman names
        if renderer.startswith('renderman'):
            renderer = 'renderman'

        file_prefix = cmds.getAttr(
            RenderSettings.get_image_prefix_attr(renderer)
        )


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
