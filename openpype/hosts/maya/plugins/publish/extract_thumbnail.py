import os
import glob
import tempfile
import json

import capture

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib

from maya import cmds


class ExtractThumbnail(publish.Extractor):
    """Extract viewport thumbnail.

    Takes review camera and creates a thumbnail based on viewport
    capture.

    """

    label = "Thumbnail"
    hosts = ["maya"]
    families = ["review"]

    def process(self, instance):
        self.log.debug("Extracting capture..")

        camera = instance.data["review_camera"]

        task_data = instance.data["anatomyData"].get("task", {})
        capture_preset = lib.get_capture_preset(
            task_data.get("name"),
            task_data.get("type"),
            instance.data["subset"],
            instance.context.data["project_settings"],
            self.log
        )

        preset = lib.load_capture_preset(data=capture_preset)

        # "isolate_view" will already have been applied at creation, so we'll
        # ignore it here.
        preset.pop("isolate_view")

        override_viewport_options = (
            capture_preset["Viewport Options"]["override_viewport_options"]
        )

        preset["camera"] = camera
        preset["start_frame"] = instance.data["frameStart"]
        preset["end_frame"] = instance.data["frameStart"]
        preset["camera_options"] = {
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
        # Set resolution variables from capture presets
        width_preset = capture_preset["Resolution"]["width"]
        height_preset = capture_preset["Resolution"]["height"]
        # Set resolution variables from asset values
        asset_data = instance.data["assetEntity"]["data"]
        asset_width = asset_data.get("resolutionWidth")
        asset_height = asset_data.get("resolutionHeight")
        review_instance_width = instance.data.get("review_width")
        review_instance_height = instance.data.get("review_height")
        # Tests if project resolution is set,
        # if it is a value other than zero, that value is
        # used, if not then the asset resolution is
        # used
        if review_instance_width and review_instance_height:
            preset["width"] = review_instance_width
            preset["height"] = review_instance_height
        elif width_preset and height_preset:
            preset["width"] = width_preset
            preset["height"] = height_preset
        elif asset_width and asset_height:
            preset["width"] = asset_width
            preset["height"] = asset_height

        # Create temp directory for thumbnail
        # - this is to avoid "override" of source file
        dst_staging = tempfile.mkdtemp(prefix="pyblish_tmp_")
        self.log.debug(
            "Create temp directory {} for thumbnail".format(dst_staging)
        )
        # Store new staging to cleanup paths
        filename = "{0}".format(instance.name)
        path = os.path.join(dst_staging, filename)

        self.log.debug("Outputting images to %s" % path)

        preset["filename"] = path
        preset["overwrite"] = True

        cmds.refresh(force=True)

        refreshFrameInt = int(cmds.playbackOptions(q=True, minTime=True))
        cmds.currentTime(refreshFrameInt - 1, edit=True)
        cmds.currentTime(refreshFrameInt, edit=True)

        # Use displayLights setting from instance
        key = "displayLights"
        preset["viewport_options"][key] = instance.data[key]

        # Override transparency if requested.
        transparency = instance.data.get("transparency", 0)
        if transparency != 0:
            preset["viewport2_options"]["transparencyAlgorithm"] = transparency

        # Isolate view is requested by having objects in the set besides a
        # camera. If there is only 1 member it'll be the camera because we
        # validate to have 1 camera only.
        if instance.data["isolate"] and len(instance.data["setMembers"]) > 1:
            preset["isolate"] = instance.data["setMembers"]

        # Show or Hide Image Plane
        image_plane = instance.data.get("imagePlane", True)
        if "viewport_options" in preset:
            preset["viewport_options"]["imagePlane"] = image_plane
        else:
            preset["viewport_options"] = {"imagePlane": image_plane}

        # Disable Pan/Zoom.
        preset.pop("pan_zoom", None)
        preset["camera_options"]["panZoomEnabled"] = instance.data["panZoom"]

        with lib.maintained_time():
            # Force viewer to False in call to capture because we have our own
            # viewer opening call to allow a signal to trigger between
            # playblast and viewer
            preset["viewer"] = False

            # Update preset with current panel setting
            # if override_viewport_options is turned off
            panel = cmds.getPanel(withFocus=True) or ""
            if not override_viewport_options and "modelPanel" in panel:
                panel_preset = capture.parse_active_view()
                preset.update(panel_preset)
                cmds.setFocus(panel)

            if os.environ.get("OPENPYPE_DEBUG") == "1":
                self.log.debug(
                    "Using preset: {}".format(
                        json.dumps(preset, indent=4, sort_keys=True)
                    )
                )

            path = capture.capture(**preset)
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
