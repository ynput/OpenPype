import maya.cmds as cmds
import maya.mel as mel

import pyblish.api


class CollectMayaUnits(pyblish.api.ContextPlugin):
    """Collect Maya's scene units."""

    label = "Maya Units"
    order = pyblish.api.CollectorOrder
    hosts = ["maya"]

    def process(self, context):

        # Get the current linear units
        units = cmds.currentUnit(query=True, linear=True)

        # Get the current angular units ('deg' or 'rad')
        units_angle = cmds.currentUnit(query=True, angle=True)

        # Get the current time units
        # Using the mel command is simpler than using
        # `cmds.currentUnit(q=1, time=1)`. Otherwise we
        # have to parse the returned string value to FPS
        fps = mel.eval('currentTimeUnitToFPS()')

        context.data['linearUnits'] = units
        context.data['angularUnits'] = units_angle
        context.data['fps'] = fps
