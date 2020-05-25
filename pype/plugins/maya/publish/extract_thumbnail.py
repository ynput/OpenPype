import os
import contextlib
import glob

import capture

from pype.hosts.maya import lib
import pype.api

from maya import cmds
import pymel.core as pm


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

        camera = instance.data['review_camera']

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
            filename = preset.get("filename", "%TEMP%")

            # Force viewer to False in call to capture because we have our own
            # viewer opening call to allow a signal to trigger between
            # playblast and viewer
            preset['viewer'] = False

            # Remove panel key since it's internal value to capture_gui
            preset.pop("panel", None)

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
