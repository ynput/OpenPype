import maya.cmds as cmds

import pyblish.api
import openpype.api
from openpype import lib
import openpype.hosts.maya.api.lib as mayalib
from math import ceil


def float_round(num, places=0, direction=ceil):
    return direction(num * (10**places)) / float(10**places)


class ValidateMayaUnits(pyblish.api.ContextPlugin):
    """Check if the Maya units are set correct"""

    order = openpype.api.ValidateSceneOrder
    label = "Maya Units"
    hosts = ['maya']
    actions = [openpype.api.RepairContextAction]

    validate_linear_units = True
    linear_units = "cm"

    validate_angular_units = True
    angular_units = "deg"

    validate_fps = True

    def process(self, context):

        # Collected units
        linearunits = context.data.get('linearUnits')
        angularunits = context.data.get('angularUnits')
        # TODO(antirotor): This is hack as for framerates having multiple
        # decimal places. FTrack is ceiling decimal values on
        # fps to two decimal places but Maya 2019+ is reporting those fps
        # with much higher resolution. As we currently cannot fix Ftrack
        # rounding, we have to round those numbers coming from Maya.
        # NOTE: this must be revisited yet again as it seems that Ftrack is
        # now flooring the value?
        fps = float_round(context.data.get('fps'), 2, ceil)

        asset_fps = lib.get_asset()["data"]["fps"]

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
        asset_fps = lib.get_asset()["data"]["fps"]
        mayalib.set_scene_fps(asset_fps)
