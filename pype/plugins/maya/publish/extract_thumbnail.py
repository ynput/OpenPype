import os
import contextlib
import time
import sys

import capture_gui
import clique

import pype.maya.lib as lib
import pype.api

from maya import cmds
import pymel.core as pm
from pype.vendor import ffmpeg
reload(ffmpeg)

import avalon.maya

# import maya_utils as mu

# from tweakHUD import master
# from tweakHUD import draft_hud as dHUD
# from tweakHUD import ftrackStrings as fStrings

#
# def soundOffsetFunc(oSF, SF, H):
#     tmOff = (oSF - H) - SF
#     return tmOff


class ExtractThumbnail(pype.api.Extractor):
    """Extract a Camera as Alembic.

    The cameras gets baked to world space by default. Only when the instance's
    `bakeToWorldSpace` is set to False it will include its full hierarchy.

    """

    label = "Thumbnail"
    hosts = ["maya"]
    families = ["review"]

    def process(self, instance):
        self.log.info("Extracting capture..")

        start = cmds.currentTime(query=True)
        end = cmds.currentTime(query=True)
        self.log.info("start: {}, end: {}".format(start, end))

        members = instance.data['setMembers']
        camera = instance.data['review_camera']

        # project_code = ftrack_data['Project']['code']
        # task_type = ftrack_data['Task']['type']
        #
        # # load Preset
        # studio_repos = os.path.abspath(os.environ.get('studio_repos'))
        # shot_preset_path = os.path.join(studio_repos, 'maya',
        #                             'capture_gui_presets',
        #                            (project_code + '_' + task_type + '_' + asset + '.json'))
        #
        # task_preset_path = os.path.join(studio_repos, 'maya',
        #                             'capture_gui_presets',
        #                            (project_code + '_' + task_type + '.json'))
        #
        # project_preset_path = os.path.join(studio_repos, 'maya',
        #                            'capture_gui_presets',
        #                            (project_code + '.json'))
        #
        # default_preset_path = os.path.join(studio_repos, 'maya',
        #                            'capture_gui_presets',
        #                            'default.json')
        #
        # if os.path.isfile(shot_preset_path):
        #     preset_to_use = shot_preset_path
        # elif os.path.isfile(task_preset_path):
        #     preset_to_use = task_preset_path
        # elif os.path.isfile(project_preset_path):
        #     preset_to_use = project_preset_path
        # else:
        #     preset_to_use = default_preset_path

        capture_preset = ""
        capture_preset = instance.context.data['presets']['maya']['capture']
        try:
            preset = lib.load_capture_preset(data=capture_preset)
        except:
            preset = {}
        self.log.info('using viewport preset: {}'.format(capture_preset))

        # preset["off_screen"] =  False

        preset['camera'] = camera
        preset['format'] = "image"
        # preset['compression'] = "qt"
        preset['quality'] = 50
        preset['compression'] = "jpg"
        preset['start_frame'] = start
        preset['end_frame'] = end
        preset['camera_options'] = {
            "displayGateMask": False,
            "displayResolution": False,
            "displayFilmGate": False,
            "displayFieldChart": False,
            "displaySafeAction": False,
            "displaySafeTitle": False,
            "displayFilmPivot": False,
            "displayFilmOrigin": False,
            "overscan": 1.0,
            "depthOfField": cmds.getAttr("{0}.depthOfField".format(camera)),
        }

        stagingDir = self.staging_dir(instance)
        filename = "{0}".format(instance.name)
        path = os.path.join(stagingDir, filename)

        self.log.info("Outputting images to %s" % path)

        preset['filename'] = path
        preset['overwrite'] = True

        pm.refresh(f=True)

        refreshFrameInt = int(pm.playbackOptions(q=True, minTime=True))
        pm.currentTime(refreshFrameInt - 1, edit=True)
        pm.currentTime(refreshFrameInt, edit=True)

        with maintained_time():
            playblast = capture_gui.lib.capture_scene(preset)

        _, thumbnail = os.path.split(playblast)

        self.log.info("file list  {}".format(thumbnail))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'thumbnail',
            'ext': 'jpg',
            'files': thumbnail,
            "stagingDir": stagingDir,
            "thumbnail": True
        }
        instance.data["representations"].append(representation)


@contextlib.contextmanager
def maintained_time():
    ct = cmds.currentTime(query=True)
    try:
        yield
    finally:
        cmds.currentTime(ct, edit=True)
