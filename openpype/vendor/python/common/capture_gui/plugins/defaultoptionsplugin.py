import capture
import capture_gui.plugin


class DefaultOptionsPlugin(capture_gui.plugin.Plugin):
    """Invisible Plugin that supplies some default values to the gui.

    This enures:
        - no HUD is present in playblasts
        - no overscan (`overscan` set to 1.0)
        - no title safe, action safe, gate mask, etc.
        - active sound is included in video playblasts

    """
    order = -1
    hidden = True

    def get_outputs(self):
        """Get the plugin outputs that matches `capture.capture` arguments

        Returns:
            dict: Plugin outputs

        """

        outputs = dict()

        # use active sound track
        scene = capture.parse_active_scene()
        outputs['sound'] = scene['sound']

        # override default settings
        outputs['show_ornaments'] = True  # never show HUD or overlays

        # override camera options
        outputs['camera_options'] = dict()
        outputs['camera_options']['overscan'] = 1.0
        outputs['camera_options']['displayFieldChart'] = False
        outputs['camera_options']['displayFilmGate'] = False
        outputs['camera_options']['displayFilmOrigin'] = False
        outputs['camera_options']['displayFilmPivot'] = False
        outputs['camera_options']['displayGateMask'] = False
        outputs['camera_options']['displayResolution'] = False
        outputs['camera_options']['displaySafeAction'] = False
        outputs['camera_options']['displaySafeTitle'] = False

        return outputs
