import maya.cmds as cmds

import pyblish.api
import pype.api
from pype import lib
import pype.maya.lib as mayalib


class ValidateMayaUnits(pyblish.api.ContextPlugin):
    """Check if the Maya units are set correct"""

    order = pype.api.ValidateSceneOrder
    label = "Maya Units"
    hosts = ['maya']
    actions = [pype.api.RepairContextAction]

    def process(self, context):

        # Collected units
        linearunits = context.data('linearUnits')
        angularunits = context.data('angularUnits')
        fps = context.data['fps']

        asset_fps = lib.get_asset()["data"]["fps"]

        self.log.info('Units (linear): {0}'.format(linearunits))
        self.log.info('Units (angular): {0}'.format(angularunits))
        self.log.info('Units (time): {0} FPS'.format(fps))

        # Check if units are correct
        assert linearunits and linearunits == 'cm', ("Scene linear units must "
                                                     "be centimeters")

        assert angularunits and angularunits == 'deg', ("Scene angular units "
                                                        "must be degrees")
        assert fps and fps == asset_fps, "Scene must be %s FPS" % asset_fps

    @classmethod
    def repair(cls, context):
        """Fix the current FPS setting of the scene, set to PAL(25.0 fps)"""

        cls.log.info("Setting angular unit to 'degrees'")
        cmds.currentUnit(angle="degree")
        current_angle = cmds.currentUnit(query=True, angle=True)
        cls.log.debug(current_angle)

        cls.log.info("Setting linear unit to 'centimeter'")
        cmds.currentUnit(linear="centimeter")
        current_linear = cmds.currentUnit(query=True, linear=True)
        cls.log.debug(current_linear)

        cls.log.info("Setting time unit to match project")
        asset_fps = lib.get_asset()["data"]["fps"]
        mayalib.set_scene_fps(asset_fps)
