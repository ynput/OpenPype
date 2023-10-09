import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from maya import cmds
from openpype.pipeline.publish import RepairAction
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.lib import reset_scene_resolution


class ValidateResolution(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validate the render resolution setting aligned with DB"""

    order = pyblish.api.ValidatorOrder
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
                "Render resolution is invalid. See log for details.",
                description=(
                    "Wrong render resolution setting. "
                    "Please use repair button to fix it.\n\n"
                    "If current renderer is V-Ray, "
                    "make sure vraySettings node has been created."
                )
            )

    @classmethod
    def get_invalid_resolution(cls, instance):
        width, height, pixelAspect = cls.get_db_resolution(instance)
        current_renderer = instance.data["renderer"]
        layer = instance.data["renderlayer"]
        invalid = False
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
                cls.log.error(
                    "Can't detect VRay resolution because there is no node "
                    "named: `{}`".format(vray_node)
                )
                return True
        else:
            current_width = lib.get_attr_in_layer(
                "defaultResolution.width", layer=layer)
            current_height = lib.get_attr_in_layer(
                "defaultResolution.height", layer=layer)
            current_pixelAspect = lib.get_attr_in_layer(
                "defaultResolution.pixelAspect", layer=layer
            )
        if current_width != width or current_height != height:
            cls.log.error(
                "Render resolution {}x{} does not match "
                "asset resolution {}x{}".format(
                    current_width, current_height,
                    width, height
                ))
            invalid = True
        if current_pixelAspect != pixelAspect:
            cls.log.error(
                "Render pixel aspect {} does not match "
                "asset pixel aspect {}".format(
                    current_pixelAspect, pixelAspect
                ))
            invalid = True
        return invalid

    @classmethod
    def get_db_resolution(cls, instance):
        asset_doc = instance.data["assetEntity"]
        project_doc = instance.context.data["projectEntity"]
        for data in [asset_doc["data"], project_doc["data"]]:
            if (
                "resolutionWidth" in data and
                "resolutionHeight" in data and
                "pixelAspect" in data
            ):
                width = data["resolutionWidth"]
                height = data["resolutionHeight"]
                pixelAspect = data["pixelAspect"]
                return int(width), int(height), float(pixelAspect)

        # Defaults if not found in asset document or project document
        return 1920, 1080, 1.0

    @classmethod
    def repair(cls, instance):
        # Usually without renderlayer overrides the renderlayers
        # all share the same resolution value - so fixing the first
        # will have fixed all the others too. It's much faster to
        # check whether it's invalid first instead of switching
        # into all layers individually
        if not cls.get_invalid_resolution(instance):
            cls.log.debug(
                "Nothing to repair on instance: {}".format(instance)
            )
            return
        layer_node = instance.data['setMembers']
        with lib.renderlayer(layer_node):
            reset_scene_resolution()
