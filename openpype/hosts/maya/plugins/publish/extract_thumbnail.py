import os
import contextlib
import glob

import capture

from openpype.hosts.maya.api import lib
import openpype.api

from maya import cmds
import pymel.core as pm


class ExtractThumbnail(openpype.api.Extractor):
    """Extract viewport thumbnail.

    Takes review camera and creates a thumbnail based on viewport
    capture.

    """

    label = "Thumbnail"
    hosts = ["maya"]
    families = ["review"]

    def process(self, instance):
        self.log.info("Extracting capture..")

        camera = instance.data['review_camera']

        capture_preset = ""
        capture_preset = (
            instance.context.data["project_settings"]['maya']['publish']['ExtractPlayblast']['capture_preset']
        )
        override_viewport_options = (
            capture_preset['Viewport Options']['override_viewport_options']
        )

        try:
            preset = lib.load_capture_preset(data=capture_preset)
        except KeyError as ke:
            self.log.error('Error loading capture presets: {}'.format(str(ke)))
            preset = {}
        self.log.info('Using viewport preset: {}'.format(preset))

        # preset["off_screen"] =  False

        preset['camera'] = camera
        preset['start_frame'] = instance.data["frameStart"]
        preset['end_frame'] = instance.data["frameStart"]
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

        # Isolate view is requested by having objects in the set besides a
        # camera.
        if preset.pop("isolate_view", False) and instance.data.get("isolate"):
            preset["isolate"] = instance.data["setMembers"]

        with maintained_time():
            filename = preset.get("filename", "%TEMP%")

            # Force viewer to False in call to capture because we have our own
            # viewer opening call to allow a signal to trigger between
            # playblast and viewer
            preset['viewer'] = False

            # Update preset with current panel setting
            # if override_viewport_options is turned off
            if not override_viewport_options:
                panel_preset = capture.parse_active_view()
                preset.update(panel_preset)

            path = capture.capture(**preset)
            playblast = self._fix_playblast_output_path(path)

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

    def _fix_playblast_output_path(self, filepath):
        """Workaround a bug in maya.cmds.playblast to return correct filepath.

        When the `viewer` argument is set to False and maya.cmds.playblast
        does not automatically open the playblasted file the returned
        filepath does not have the file's extension added correctly.

        To workaround this we just glob.glob() for any file extensions and
         assume the latest modified file is the correct file and return it.

        """
        # Catch cancelled playblast
        if filepath is None:
            self.log.warning("Playblast did not result in output path. "
                             "Playblast is probably interrupted.")
            return None

        # Fix: playblast not returning correct filename (with extension)
        # Lets assume the most recently modified file is the correct one.
        if not os.path.exists(filepath):
            directory = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            # check if the filepath is has frame based filename
            # example : capture.####.png
            parts = filename.split(".")
            if len(parts) == 3:
                query = os.path.join(directory, "{}.*.{}".format(parts[0],
                                                                 parts[-1]))
                files = glob.glob(query)
            else:
                files = glob.glob("{}.*".format(filepath))

            if not files:
                raise RuntimeError("Couldn't find playblast from: "
                                   "{0}".format(filepath))
            filepath = max(files, key=os.path.getmtime)

        return filepath


@contextlib.contextmanager
def maintained_time():
    ct = cmds.currentTime(query=True)
    try:
        yield
    finally:
        cmds.currentTime(ct, edit=True)
