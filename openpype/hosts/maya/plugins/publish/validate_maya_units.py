import maya.cmds as cmds

import pyblish.api

import openpype.hosts.maya.api.lib as mayalib
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.pipeline.publish import (
    RepairContextAction,
    ValidateSceneOrder,
    PublishXmlValidationError
)


class ValidateMayaUnits(pyblish.api.ContextPlugin):
    """Check if the Maya units are set correct"""

    order = ValidateSceneOrder
    label = "Maya Units"
    hosts = ['maya']
    actions = [RepairContextAction]

    validate_linear_units = True
    linear_units = "cm"

    validate_angular_units = True
    angular_units = "deg"

    validate_fps = True

    nice_message_format = (
        "- <b>{setting}</b> must be <b>{required_value}</b>.  "
        "Your scene is set to <b>{current_value}</b>"
    )
    log_message_format = (
        "Maya scene {setting} must be '{required_value}'. "
        "Current value is '{current_value}'."
    )

    @classmethod
    def apply_settings(cls, project_settings):
        """Apply project settings to creator"""
        settings = (
            project_settings["maya"]["publish"]["ValidateMayaUnits"]
        )

        cls.validate_linear_units = settings.get("validate_linear_units",
                                                 cls.validate_linear_units)
        cls.linear_units = settings.get("linear_units", cls.linear_units)
        cls.validate_angular_units = settings.get("validate_angular_units",
                                                  cls.validate_angular_units)
        cls.angular_units = settings.get("angular_units", cls.angular_units)
        cls.validate_fps = settings.get("validate_fps", cls.validate_fps)

    def process(self, context):

        # Collected units
        linearunits = context.data.get('linearUnits')
        angularunits = context.data.get('angularUnits')

        fps = context.data.get('fps')

        asset_doc = context.data["assetEntity"]
        asset_fps = mayalib.convert_to_maya_fps(asset_doc["data"]["fps"])

        self.log.info('Units (linear): {0}'.format(linearunits))
        self.log.info('Units (angular): {0}'.format(angularunits))
        self.log.info('Units (time): {0} FPS'.format(fps))

        invalid = []

        # Check if units are correct
        if (
            self.validate_linear_units
            and linearunits
            and linearunits != self.linear_units
        ):
            invalid.append({
                "setting": "Linear units",
                "required_value": self.linear_units,
                "current_value": linearunits
            })

        if (
            self.validate_angular_units
            and angularunits
            and angularunits != self.angular_units
        ):
            invalid.append({
                "setting": "Angular units",
                "required_value": self.angular_units,
                "current_value": angularunits
            })

        if self.validate_fps and fps and fps != asset_fps:
            invalid.append({
                "setting": "FPS",
                "required_value": asset_fps,
                "current_value": fps
            })

        if invalid:

            issues = []
            for data in invalid:
                self.log.error(self.log_message_format.format(**data))
                issues.append(self.nice_message_format.format(**data))
            issues = "\n".join(issues)

            raise PublishXmlValidationError(
                plugin=self,
                message="Invalid maya scene units",
                formatting_data={"issues": issues}
            )

    @classmethod
    def repair(cls, context):
        """Fix the current FPS setting of the scene, set to PAL(25.0 fps)"""

        cls.log.info("Setting angular unit to '{}'".format(cls.angular_units))
        cmds.currentUnit(angle=cls.angular_units)
        current_angle = cmds.currentUnit(query=True, angle=True)
        cls.log.debug(current_angle)

        cls.log.info("Setting linear unit to '{}'".format(cls.linear_units))
        cmds.currentUnit(linear=cls.linear_units)
        current_linear = cmds.currentUnit(query=True, linear=True)
        cls.log.debug(current_linear)

        cls.log.info("Setting time unit to match project")
        # TODO replace query with using 'context.data["assetEntity"]'
        asset_doc = get_current_project_asset()
        asset_fps = asset_doc["data"]["fps"]
        mayalib.set_scene_fps(asset_fps)
