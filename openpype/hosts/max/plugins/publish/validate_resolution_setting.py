import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from pymxs import runtime as rt
from openpype.hosts.max.api.lib import reset_scene_resolution

from openpype.pipeline.context_tools import (
    get_current_project_asset,
    get_current_project
)


class ValidateResolutionSetting(pyblish.api.InstancePlugin,
                                OptionalPyblishPluginMixin):
    """Validate the resolution setting aligned with DB"""

    order = pyblish.api.ValidatorOrder - 0.01
    families = ["maxrender"]
    hosts = ["max"]
    label = "Validate Resolution Setting"
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        width, height = self.get_db_resolution(instance)
        current_width = rt.renderwidth
        current_height = rt.renderHeight
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
        data = ["data.resolutionWidth", "data.resolutionHeight"]
        project_resolution = get_current_project(fields=data)
        project_resolution_data = project_resolution["data"]
        asset_resolution = get_current_project_asset(fields=data)
        asset_resolution_data = asset_resolution["data"]
        # Set project resolution
        project_width = int(
            project_resolution_data.get("resolutionWidth", 1920))
        project_height = int(
            project_resolution_data.get("resolutionHeight", 1080))
        width = int(
            asset_resolution_data.get("resolutionWidth", project_width))
        height = int(
            asset_resolution_data.get("resolutionHeight", project_height))

        return width, height

    @classmethod
    def repair(cls, instance):
        reset_scene_resolution()
