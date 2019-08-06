import nuke
import os
import pyblish.api
import avalon.io as io
# TODO: add repair function


@pyblish.api.log
class ValidateSettingsNuke(pyblish.api.Validator):
    """ Validates settings """

    families = ['scene']
    hosts = ['nuke']
    optional = True
    label = 'Settings'

    def process(self, instance):

        asset = io.find_one({"name": os.environ['AVALON_ASSET']})
        try:
            avalon_resolution = asset["data"].get("resolution", '')
            avalon_pixel_aspect = asset["data"].get("pixelAspect", '')
            avalon_fps = asset["data"].get("fps", '')
            avalon_first = asset["data"].get("frameStart", '')
            avalon_last = asset["data"].get("frameEnd", '')
            avalon_crop = asset["data"].get("crop", '')
        except KeyError:
            print(
                "No resolution information found for \"{0}\".".format(
                    asset["name"]
                )
            )
            return

        # validating first frame
        local_first = nuke.root()['first_frame'].value()
        msg = 'First frame is incorrect.'
        msg += '\n\nLocal first: %s' % local_first
        msg += '\n\nOnline first: %s' % avalon_first
        assert local_first == avalon_first, msg

        # validating last frame
        local_last = nuke.root()['last_frame'].value()
        msg = 'Last frame is incorrect.'
        msg += '\n\nLocal last: %s' % local_last
        msg += '\n\nOnline last: %s' % avalon_last
        assert local_last == avalon_last, msg

        # validating fps
        local_fps = nuke.root()['fps'].value()
        msg = 'FPS is incorrect.'
        msg += '\n\nLocal fps: %s' % local_fps
        msg += '\n\nOnline fps: %s' % avalon_fps
        assert local_fps == avalon_fps, msg

        # validating resolution width
        local_width = nuke.root().format().width()
        msg = 'Width is incorrect.'
        msg += '\n\nLocal width: %s' % local_width
        msg += '\n\nOnline width: %s' % avalon_resolution[0]
        assert local_width == avalon_resolution[0], msg

        # validating resolution width
        local_height = nuke.root().format().height()
        msg = 'Height is incorrect.'
        msg += '\n\nLocal height: %s' % local_height
        msg += '\n\nOnline height: %s' % avalon_resolution[1]
        assert local_height == avalon_resolution[1], msg
