import os
import contextlib
import time

import capture_gui

import pype.maya.lib as lib
import pype.api

from maya import cmds
import pymel.core as pm


import avalon.maya

# import maya_utils as mu

# from tweakHUD import master
# from tweakHUD import draft_hud as dHUD
# from tweakHUD import ftrackStrings as fStrings

#
# def soundOffsetFunc(oSF, SF, H):
#     tmOff = (oSF - H) - SF
#     return tmOff


class ExtractQuicktime(pype.api.Extractor):
    """Extract a Camera as Alembic.

    The cameras gets baked to world space by default. Only when the instance's
    `bakeToWorldSpace` is set to False it will include its full hierarchy.

    """

    label = "Quicktime (Alembic)"
    hosts = ["maya"]
    families = ["review"]

    def process(self, instance):
        self.log.info("Extracting capture..")

        start = instance.data["startFrame"]
        end = instance.data["endFrame"]
        self.log.info("start: {}, end: {}".format(start, end))
        handles = instance.data.get("handles", 0)
        if handles:
            start -= handles
            end += handles

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, leaf=True, shapes=True, long=True,
                          dag=True, type="camera")

        # validate required settings
        assert len(cameras) == 1, "Not a single camera found in extraction"
        camera = cameras[0]


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
        try:
            preset = lib.load_capture_preset(capture_preset)
        except:
            preset = {}
        self.log.info('using viewport preset: {}'.format(capture_preset))

        #preset["off_screen"] =  False

        preset['camera'] = camera
        preset['format'] = "image"
        # preset['compression'] = "qt"
        preset['quality'] = 50
        preset['compression'] = "jpg"
        preset['start_frame'] = 1
        preset['end_frame'] = 25
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

        stagingdir = self.staging_dir(instance)
        filename = "{0}".format(instance.name)
        path = os.path.join(stagingdir, filename)

        self.log.info("Outputting images to %s" % path)

        preset['filename'] = path
        preset['overwrite'] = True

        # pm.refresh(f=True)
        #
        # refreshFrameInt = int(pm.playbackOptions(q=True, minTime=True))
        # pm.currentTime(refreshFrameInt - 1, edit=True)
        # pm.currentTime(refreshFrameInt, edit=True)

        with maintained_time():
            playblast = capture_gui.lib.capture_scene(preset)

        if "files" not in instance.data:
            instance.data["files"] = list()
        instance.data["files"].append(playblast)






        # self.log.info("Calculating HUD data overlay")

        # movieFullPth = path + ".mov"
        # fls = [os.path.join(dir_path, f).replace("\\","/") for f in os.listdir( dir_path ) if f.endswith(preset['compression'])]
        #self.log.info(" these  %s" % fls[0])

        # ftrackStrings = fStrings.annotationData()
        # nData = ftrackStrings.niceData
        # nData['version'] = instance.context.data('version')
        # fFrame = int(pm.playbackOptions( q = True,  minTime = True))
        # eFrame = int(pm.playbackOptions( q = True,  maxTime = True))
        # nData['frame'] = [(str("{0:05d}".format(f))) for f in range(fFrame, eFrame + 1)]
        # soundOfst = int(float(nData['oFStart'])) - int(float(nData['handle'])) - fFrame
        # soundFile = mu.giveMePublishedAudio()
        # self.log.info("SOUND offset  %s" % str(soundOfst))
        # self.log.info("SOUND source video to %s" % str(soundFile))
        # ann = dHUD.draftAnnotate()
        # if soundFile:
        #     ann.addAnotation(seqFls = fls, outputMoviePth = movieFullPth, annotateDataArr = nData, soundFile = soundFile, soundOffset = soundOfst)
        # else:
        #     ann.addAnotation(seqFls = fls, outputMoviePth = movieFullPth, annotateDataArr = nData)

        # for f in fls:
        #     os.remove(f)

        # playblast = (ann.expPth).replace("\\","/")


        instance.data["outputPath_qt"] = playblast
        self.log.info("Outputting video to %s" % playblast)


@contextlib.contextmanager
def maintained_time():
    ct = cmds.currentTime(query=True)
    try:
        yield
    finally:
        cmds.currentTime(ct, edit=True)
