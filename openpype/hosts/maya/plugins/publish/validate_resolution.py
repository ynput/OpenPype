import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from maya import cmds
from openpype.pipeline.publish import RepairAction
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.lib import reset_scene_resolution


class ValidateSceneResolution(pyblish.api.InstancePlugin,
                              OptionalPyblishPluginMixin):
    """Validate the scene resolution setting aligned with DB"""

    order = pyblish.api.ValidatorOrder - 0.01
    families = ["renderlayer"]
    hosts = ["maya"]
    label = "Validate Resolution"
    actions = [RepairAction]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        width, height, pixelAspect = self.get_db_resolution(instance)
        current_renderer = cmds.getAttr(
            "defaultRenderGlobals.currentRenderer")
        layer = instance.data["renderlayer"]
        if current_renderer == "vray":
            vray_node = "vraySettings"
            if cmds.objExists(vray_node):
                control_node = vray_node
                current_width = lib.get_attr_in_layer(
                    "{}.width".format(control_node), layer=layer)
                current_height = lib.get_attr_in_layer(
                    "{}.height".format(control_node), layer=layer)
                current_pixelAspect = lib.get_attr_in_layer(
                    "{}.pixelAspect".format(control_node), layer=layer
                )
            else:
                raise PublishValidationError(
                    "Can't set VRay resolution because there is no node "
                    "named: `%s`" % vray_node)
        else:
            current_width = lib.get_attr_in_layer(
                "defaultResolution.width", layer=layer)
            current_height = lib.get_attr_in_layer(
                "defaultResolution.height", layer=layer)
            current_pixelAspect = lib.get_attr_in_layer(
                "defaultResolution.pixelAspect", layer=layer
            )
        if current_width != width or current_height != height:
            raise PublishValidationError(
                "Render resolution is {}x{} does not match asset resolution is {}x{}".format(
                    current_width, current_height, width, height
                ))
        if current_pixelAspect != pixelAspect:
                raise PublishValidationError(
                "Render pixel aspect is {} does not match asset pixel aspect is {}".format(
                    current_pixelAspect, pixelAspect
                ))

    def get_db_resolution(self, instance):
        asset_doc = instance.data["assetEntity"]
        project_doc = instance.context.data["projectEntity"]
        for data in [asset_doc["data"], project_doc["data"]]:
            if "resolutionWidth" in data and "resolutionHeight" in data \
                and "pixelAspect" in data:
                width = data["resolutionWidth"]
                height = data["resolutionHeight"]
                pixelAspect = data["pixelAspect"]
                return int(width), int(height), int(pixelAspect)

        # Defaults if not found in asset document or project document
        return 1920, 1080, 1

    @classmethod
    def repair(cls, instance):
        return reset_scene_resolution()
