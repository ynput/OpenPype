import maya.cmds as cmds

import pyblish.api

import openpype.hosts.maya.api.lib as mayalib
from math import ceil
import decimal

from openpype.pipeline.publish import (
    RepairContextAction,
    ValidateSceneOrder,
)


def float_round(num, places=0, direction=ceil):
    return direction(num * (10**places)) / float(10**places)


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
        linear_units = context.data.get('linearUnits')
        angular_units = context.data.get('angularUnits')
        fps = context.data.get('fps')
        # get number of decimal places on fps
        fps_decimal_places = abs(decimal.Decimal(
            str(fps)).as_tuple()[2])

        asset_doc = context.data["assetEntity"]
        asset_fps = asset_doc["data"]["fps"]
        # get asset fps decimal places
        asset_fps_decimal_places = abs(decimal.Decimal(
            str(asset_fps)).as_tuple()[2])

        # compare only the same number of decimal places
        # normalize number of decimal places base on the number with
        # less precision.
        if asset_fps_decimal_places > fps_decimal_places:
            asset_fps = float_round(asset_fps, fps_decimal_places, ceil)
        elif asset_fps_decimal_places < fps_decimal_places:
            fps = float_round(fps, asset_fps_decimal_places, ceil)

        self.log.info('Units (linear): {0}'.format(linear_units))
        self.log.info('Units (angular): {0}'.format(angular_units))
        self.log.info('Units (time): {0} FPS'.format(context.data.get('fps')))

        valid = True

        # Check if units are correct
        if (
            self.validate_linear_units
            and linear_units
            and linear_units != self.linear_units
        ):
            self.log.error("Scene linear units must be {}".format(
                self.linear_units))
            valid = False

        if (
            self.validate_angular_units
            and angular_units
            and angular_units != self.angular_units
        ):
            self.log.error("Scene angular units must be {}".format(
                self.angular_units))
            valid = False

        if self.validate_fps and fps and fps != asset_fps:
            self.log.error(
                "Scene must be {} FPS (now is {})".format(
                    asset_doc["data"]["fps"],
                    context.data.get('fps')))
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
        asset_doc = context.data["assetEntity"]
        asset_fps = asset_doc["data"]["fps"]
        asset_fps = float_round(asset_fps, 2, ceil)
        mayalib.set_scene_fps(asset_fps)
