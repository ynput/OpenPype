import pyblish.api
import colorbleed.api


class ValidateUnitsAngular(pyblish.api.ContextPlugin):
    """Scene angular units must be in degrees"""

    order = colorbleed.api.ValidateSceneOrder
    label = "Units (angular)"
    families = ["colorbleed.rig",
                "colorbleed.model",
                "colorbleed.pointcache",
                "colorbleed.curves"]

    def process(self, context):
        units = context.data('angularUnits')

        self.log.info('Units (angular): {0}'.format(units))
        assert units and units == 'deg', (
            "Scene angular units must be degrees")
