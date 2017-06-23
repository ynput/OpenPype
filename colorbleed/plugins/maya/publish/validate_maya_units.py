import pyblish.api
import colorbleed.api


class ValidateMayaUnits(pyblish.api.ContextPlugin):
    """Check if the Maya units are set correct"""

    order = colorbleed.api.ValidateSceneOrder
    label = "Maya Units"
    families = ["colorbleed.rig",
                "colorbleed.model",
                "colorbleed.pointcache",
                "colorbleed.curves"]
    actions = [colorbleed.api.RepairAction]

    def process(self, context):

        linearunits = context.data('linearUnits')
        angularunits = context.data('angularUnits')
        fps = context.data['fps']

        self.log.info('Units (linear): {0}'.format(linearunits))
        self.log.info('Units (angular): {0}'.format(angularunits))
        self.log.info('Units (time): {0} FPS'.format(fps))

        # check if units are correct
        assert linearunits and linearunits == 'cm', ("Scene linear units must "
                                                     "be centimeters")

        assert angularunits and angularunits == 'deg', ("Scene angular units "
                                                        "must be degrees")

        assert fps and fps == 25.0, "Scene must be 25 FP"

    @classmethod
    def repair(cls):
        """Fix the current FPS setting of the scene, set to PAL(25.0 fps)
        """
        raise NotImplementedError()
