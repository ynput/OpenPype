import pyblish.api
from pymxs import runtime as rt

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError
)
from openpype.hosts.max.api.action import SelectInvalidAction


class ValidateCameraAttributes(OptionalPyblishPluginMixin,
                               pyblish.api.InstancePlugin):
    """Validates Camera has no invalid attribute properties
    or values.(For 3dsMax Cameras only)

    """

    order = pyblish.api.ValidatorOrder
    families = ['camera']
    hosts = ['max']
    label = 'Camera Attributes'
    actions = [SelectInvalidAction]
    optional = True

    DEFAULTS = ["fov", "nearrange", "farrange",
                "nearclip","farclip"]
    CAM_TYPE = ["Freecamera", "Targetcamera",
                "Physical"]

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        cameras = instance.data["members"]
        project_settings = instance.context.data["project_settings"].get("max")
        cam_attr_settings = project_settings["publish"]["ValidateCameraAttributes"]
        for camera in cameras:
            if str(rt.ClassOf(camera)) not in cls.CAM_TYPE:
                cls.log.debug(
                    "Skipping camera created from external plugin..")
                continue
            for attr in cls.DEFAULTS:
                default_value = cam_attr_settings.get(attr)
                if rt.getProperty(camera, attr) != default_value:
                    cls.log.error(
                        f"Invalid attribute value: {attr} "
                        f"(should be: {default_value}))")
                    invalid.append(camera)

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            self.log.debug("Skipping Validate Camera Attributes...")
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                f"Invalid camera attributes: {invalid}")
