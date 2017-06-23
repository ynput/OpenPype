import pyblish.api
import colorbleed.api


class ValidateUnitsFps(pyblish.api.ContextPlugin):
    """Validate the scene linear, angular and time units."""

    order = colorbleed.api.ValidateSceneOrder
    label = "Units (fps)"
    families = ["colorbleed.rig",
                "colorbleed.pointcache",
                "colorbleed.curves"]
    actions = [colorbleed.api.RepairAction]
    optional = True

    def process(self, context):

        fps = context.data['fps']

        self.log.info('Units (time): {0} FPS'.format(fps))
        assert fps and fps == 25.0, "Scene must be 25 FPS"

    @classmethod
    def repair(cls):
        """Fix the current FPS setting of the scene, set to PAL(25.0 fps)
        """
        import maya.cmds as cmds
        cmds.currentUnit(time="pal")
