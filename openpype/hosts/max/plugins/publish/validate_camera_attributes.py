import pyblish.api
from pymxs import runtime as rt

from openpype.pipeline.publish import (
    RepairAction,
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
    label = 'Validate Camera Attributes'
    actions = [SelectInvalidAction, RepairAction]
    optional = True

    DEFAULTS = ["fov", "nearrange", "farrange",
                "nearclip", "farclip"]
    CAM_TYPE = ["Freecamera", "Targetcamera",
                "Physical"]

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        if rt.units.DisplayType != rt.Name("Generic"):
            cls.log.warning(
                "Generic Type is not used as a scene unit\n\n"
                "sure you tweak the settings with your own values\n\n"
                "before validation.")
        cameras = instance.data["members"]
        project_settings = instance.context.data["project_settings"].get("max")
        cam_attr_settings = (
            project_settings["publish"]["ValidateCameraAttributes"]
        )
        for camera in cameras:
            if str(rt.ClassOf(camera)) not in cls.CAM_TYPE:
                cls.log.debug(
                    "Skipping camera created from external plugin..")
                continue
            for attr in cls.DEFAULTS:
                default_value = cam_attr_settings.get(attr)
                if default_value == float(0):
                    cls.log.debug(
                        f"the value of {attr} in setting set to"
                        " zero. Skipping the check.")
                    continue
                if round(rt.getProperty(camera, attr), 1) != default_value:
                    cls.log.error(
                        f"Invalid attribute value for {camera.name}:{attr} "
                        f"(should be: {default_value}))")
                    invalid.append(camera)

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            self.log.debug("Skipping Validate Camera Attributes.")
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Invalid camera attributes found. See log.")

    @classmethod
    def repair(cls, instance):
        invalid_cameras = cls.get_invalid(instance)
        project_settings = instance.context.data["project_settings"].get("max")
        cam_attr_settings = (
            project_settings["publish"]["ValidateCameraAttributes"]
        )
        for camera in invalid_cameras:
            for attr in cls.DEFAULTS:
                expected_value = cam_attr_settings.get(attr)
                if expected_value == float(0):
                    cls.log.debug(
                        f"the value of {attr} in setting set to zero.")
                    continue
                rt.setProperty(camera, attr, expected_value)
