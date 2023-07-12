import maya.cmds as cmds

import pyblish.api

import openpype.hosts.maya.api.lib as mayalib
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.pipeline.publish import (
    RepairContextAction,
    ValidateSceneOrder,
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

    def process(self, context):

        # Collected units
        linearunits = context.data.get('linearUnits')
        angularunits = context.data.get('angularUnits')

        fps = context.data.get('fps')

        # TODO replace query with using 'context.data["assetEntity"]'
        asset_doc = get_current_project_asset()
        asset_fps = mayalib.convert_to_maya_fps(asset_doc["data"]["fps"])

        self.log.info('Units (linear): {0}'.format(linearunits))
        self.log.info('Units (angular): {0}'.format(angularunits))
        self.log.info('Units (time): {0} FPS'.format(fps))

        valid = True

        # Check if units are correct
        if (
            self.validate_linear_units
            and linearunits
            and linearunits != self.linear_units
        ):
            self.log.error("Scene linear units must be {}".format(
                self.linear_units))
            valid = False

        if (
            self.validate_angular_units
            and angularunits
            and angularunits != self.angular_units
        ):
            self.log.error("Scene angular units must be {}".format(
                self.angular_units))
            valid = False

        if self.validate_fps and fps and fps != asset_fps:
            self.log.error(
                "Scene must be {} FPS (now is {})".format(asset_fps, fps))
            valid = False

        if not valid:
            raise RuntimeError("Invalid units set.")

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
