import os
import glob
import tempfile

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib


class ExtractThumbnail(publish.Extractor):
    """Extract viewport thumbnail.

    Takes review camera and creates a thumbnail based on viewport
    capture.

    """

    label = "Thumbnail"
    hosts = ["maya"]
    families = ["review"]

    def process(self, instance):
        self.log.debug("Extracting thumbnail..")

        camera = instance.data["review_camera"]

        task_data = instance.data["anatomyData"].get("task", {})
        capture_preset = lib.get_capture_preset(
            task_data.get("name"),
            task_data.get("type"),
            instance.data["subset"],
            instance.context.data["project_settings"],
            self.log
        )

        # Create temp directory for thumbnail
        # - this is to avoid "override" of source file
        dst_staging = tempfile.mkdtemp(prefix="pyblish_tmp_thumbnail")
        self.log.debug(
            "Create temp directory {} for thumbnail".format(dst_staging)
        )
        # Store new staging to cleanup paths
        filename = instance.name
        path = os.path.join(dst_staging, filename)

        self.log.debug("Outputting images to %s" % path)

        preset = lib.generate_capture_preset(
            instance, camera, path,
            start=1, end=1,
            capture_preset=capture_preset)

        preset["camera_options"].update({
            "displayGateMask": False,
            "displayResolution": False,
            "displayFilmGate": False,
            "displayFieldChart": False,
            "displaySafeAction": False,
            "displaySafeTitle": False,
            "displayFilmPivot": False,
            "displayFilmOrigin": False,
            "overscan": 1.0,
        })
        path = lib.render_capture_preset(preset)

        playblast = self._fix_playblast_output_path(path)

        _, thumbnail = os.path.split(playblast)

        self.log.debug("file list  {}".format(thumbnail))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "thumbnail",
            "ext": "jpg",
            "files": thumbnail,
            "stagingDir": dst_staging,
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
