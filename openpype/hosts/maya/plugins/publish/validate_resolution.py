import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from maya import cmds
from openpype.hosts.maya.api.lib import reset_scene_resolution


class ValidateResolution(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validate the resolution setting aligned with DB"""

    order = pyblish.api.ValidatorOrder - 0.01
    families = ["renderlayer"]
    hosts = ["maya"]
    label = "Validate Resolution"
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        width, height = self.get_db_resolution(instance)
        current_width = cmds.getAttr("defaultResolution.width")
        current_height = cmds.getAttr("defaultResolution.height")
        if current_width != width and current_height != height:
            raise PublishValidationError("Resolution Setting "
                                         "not matching resolution "
                                         "set on asset or shot.")
        if current_width != width:
            raise PublishValidationError("Width in Resolution Setting "
                                         "not matching resolution set "
                                         "on asset or shot.")

        if current_height != height:
            raise PublishValidationError("Height in Resolution Setting "
                                         "not matching resolution set "
                                         "on asset or shot.")

    def get_db_resolution(self, instance):
        asset_doc = instance.data["assetEntity"]
        project_doc = instance.context.data["projectEntity"]
        for data in [asset_doc["data"], project_doc["data"]]:
            if "resolutionWidth" in data and "resolutionHeight" in data:
                width = data["resolutionWidth"]
                height = data["resolutionHeight"]
                return int(width), int(height)

        # Defaults if not found in asset document or project document
        return 1920, 1080

    @classmethod
    def repair(cls, instance):
        return reset_scene_resolution()
