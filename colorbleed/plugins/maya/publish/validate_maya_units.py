import maya.cmds as cmds

import pyblish.api
import colorbleed.api
from colorbleed import lib
import colorbleed.maya.lib as mayalib


class ValidateMayaUnits(pyblish.api.ContextPlugin):
    """Check if the Maya units are set correct"""

    order = colorbleed.api.ValidateSceneOrder
    label = "Maya Units"
    hosts = ['maya']
    actions = [colorbleed.api.RepairContextAction]

    def process(self, context):

        linearunits = context.data('linearUnits')
        angularunits = context.data('angularUnits')

        fps = context.data['fps']
        project_fps = lib.get_project_fps()

        self.log.info('Units (linear): {0}'.format(linearunits))
        self.log.info('Units (angular): {0}'.format(angularunits))
        self.log.info('Units (time): {0} FPS'.format(fps))

        # Check if units are correct
        assert linearunits and linearunits == 'cm', ("Scene linear units must "
                                                     "be centimeters")

        assert angularunits and angularunits == 'deg', ("Scene angular units "
                                                        "must be degrees")
        assert fps and fps == project_fps, "Scene must be %s FPS" % project_fps

    @classmethod
    def repair(cls):
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
        mayalib.set_project_fps()
