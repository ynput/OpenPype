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
    """Validate the render resolution setting aligned with DB"""

    order = pyblish.api.ValidatorOrder - 0.01
    families = ["renderlayer"]
    hosts = ["maya"]
    label = "Validate Resolution"
    actions = [RepairAction]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid_resolution(instance)
        if invalid:
            raise PublishValidationError(
                "issues occurred", description=(
                    "Wrong render resolution setting. "
                    "Please use repair button to fix it.\n"
                    "If current renderer is V-Ray, "
                    "make sure vraySettings node has been created"
        ))

    def get_invalid_resolution(self, instance):
        width, height, pixelAspect = self.get_db_resolution(instance)
        current_renderer = cmds.getAttr(
            "defaultRenderGlobals.currentRenderer")
        layer = instance.data["renderlayer"]
        invalids = []
        if current_renderer == "vray":
            vray_node = "vraySettings"
            if cmds.objExists(vray_node):
                current_width = lib.get_attr_in_layer(
                    "{}.width".format(vray_node), layer=layer)
                current_height = lib.get_attr_in_layer(
                    "{}.height".format(vray_node), layer=layer)
                current_pixelAspect = lib.get_attr_in_layer(
                    "{}.pixelAspect".format(vray_node), layer=layer
                )
            else:
                invalid = self.log.error(
                    "Can't detect VRay resolution because there is no node "
                    "named: `{}`".format(vray_node)
                )
                invalids.append(invalid)
        else:
            current_width = lib.get_attr_in_layer(
                "defaultResolution.width", layer=layer)
            current_height = lib.get_attr_in_layer(
                "defaultResolution.height", layer=layer)
            current_pixelAspect = lib.get_attr_in_layer(
                "defaultResolution.pixelAspect", layer=layer
            )
        if current_width != width or current_height != height:
            invalid = self.log.error(
                "Render resolution {}x{} does not match asset resolution {}x{}".format(         # noqa:E501
                    current_width, current_height,
                    width, height
                ))
            invalids.append("{0}\n".format(invalid))
        if current_pixelAspect != pixelAspect:
            invalid = self.log.error(
                "Render pixel aspect {} does not match asset pixel aspect {}".format(            # noqa:E501
                    current_pixelAspect, pixelAspect
                ))
            invalids.append("{0}\n".format(invalid))
        return invalids

    def get_db_resolution(self, instance):
        asset_doc = instance.data["assetEntity"]
        project_doc = instance.context.data["projectEntity"]
        for data in [asset_doc["data"], project_doc["data"]]:
            if "resolutionWidth" in data and (
                "resolutionHeight" in data and "pixelAspect" in data
            ):
                width = data["resolutionWidth"]
                height = data["resolutionHeight"]
                pixelAspect = data["pixelAspect"]
                return int(width), int(height), float(pixelAspect)

        # Defaults if not found in asset document or project document
        return 1920, 1080, 1.0

    @classmethod
    def repair(cls, instance):
        layer = instance.data["renderlayer"]
        with lib.renderlayer(layer):
            reset_scene_resolution()
