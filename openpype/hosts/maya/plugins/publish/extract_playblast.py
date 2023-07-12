import os
import json
import contextlib

import clique
import capture

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib

from maya import cmds


@contextlib.contextmanager
def panel_camera(panel, camera):
    original_camera = cmds.modelPanel(panel, query=True, camera=True)
    try:
        cmds.modelPanel(panel, edit=True, camera=camera)
        yield
    finally:
        cmds.modelPanel(panel, edit=True, camera=original_camera)


class ExtractPlayblast(publish.Extractor):
    """Extract viewport playblast.

    Takes review camera and creates review Quicktime video based on viewport
    capture.

    """

    label = "Extract Playblast"
    hosts = ["maya"]
    families = ["review"]
    optional = True
    capture_preset = {}
    profiles = None

    def _capture(self, preset):
        if os.environ.get("OPENPYPE_DEBUG") == "1":
            self.log.debug(
                "Using preset: {}".format(
                    json.dumps(preset, indent=4, sort_keys=True)
                )
            )

        path = capture.capture(log=self.log, **preset)
        self.log.debug("playblast path  {}".format(path))

    def process(self, instance):
        self.log.info("Extracting capture..")

        # get scene fps
        fps = instance.data.get("fps") or instance.context.data.get("fps")

        # if start and end frames cannot be determined, get them
        # from Maya timeline
        start = instance.data.get("frameStartFtrack")
        end = instance.data.get("frameEndFtrack")
        if start is None:
            start = cmds.playbackOptions(query=True, animationStartTime=True)
        if end is None:
            end = cmds.playbackOptions(query=True, animationEndTime=True)

        self.log.info("start: {}, end: {}".format(start, end))

        # get cameras
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

        # Set resolution variables from capture presets
        width_preset = capture_preset["Resolution"]["width"]
        height_preset = capture_preset["Resolution"]["height"]

        # Set resolution variables from asset values
        asset_data = instance.data["assetEntity"]["data"]
        asset_width = asset_data.get("resolutionWidth")
        asset_height = asset_data.get("resolutionHeight")
        review_instance_width = instance.data.get("review_width")
        review_instance_height = instance.data.get("review_height")
        preset["camera"] = camera

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
        preset["start_frame"] = start
        preset["end_frame"] = end

        # Enforce persisting camera depth of field
        camera_options = preset.setdefault("camera_options", {})
        camera_options["depthOfField"] = cmds.getAttr(
            "{0}.depthOfField".format(camera))

        stagingdir = self.staging_dir(instance)
        filename = "{0}".format(instance.name)
        path = os.path.join(stagingdir, filename)

        self.log.info("Outputting images to %s" % path)

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

        # Show/Hide image planes on request.
        image_plane = instance.data.get("imagePlane", True)
        if "viewport_options" in preset:
            preset["viewport_options"]["imagePlane"] = image_plane
        else:
            preset["viewport_options"] = {"imagePlane": image_plane}

        # Disable Pan/Zoom.
        pan_zoom = cmds.getAttr("{}.panZoomEnabled".format(preset["camera"]))
        preset.pop("pan_zoom", None)
        preset["camera_options"]["panZoomEnabled"] = instance.data["panZoom"]

        # Need to explicitly enable some viewport changes so the viewport is
        # refreshed ahead of playblasting.
        keys = [
            "useDefaultMaterial",
            "wireframeOnShaded",
            "xray",
            "jointXray",
            "backfaceCulling"
        ]
        viewport_defaults = {}
        for key in keys:
            viewport_defaults[key] = cmds.modelEditor(
                instance.data["panel"], query=True, **{key: True}
            )
            if preset["viewport_options"][key]:
                cmds.modelEditor(
                    instance.data["panel"], edit=True, **{key: True}
                )

        override_viewport_options = (
            capture_preset["Viewport Options"]["override_viewport_options"]
        )

        # Force viewer to False in call to capture because we have our own
        # viewer opening call to allow a signal to trigger between
        # playblast and viewer
        preset["viewer"] = False

        # Update preset with current panel setting
        # if override_viewport_options is turned off
        if not override_viewport_options:
            panel_preset = capture.parse_view(instance.data["panel"])
            panel_preset.pop("camera")
            preset.update(panel_preset)

        # Need to ensure Python 2 compatibility.
        # TODO: Remove once dropping Python 2.
        if getattr(contextlib, "nested", None):
            # Python 3 compatibility.
            with contextlib.nested(
                lib.maintained_time(),
                panel_camera(instance.data["panel"], preset["camera"])
            ):
                self._capture(preset)
        else:
            # Python 2 compatibility.
            with contextlib.ExitStack() as stack:
                stack.enter_context(lib.maintained_time())
                stack.enter_context(
                    panel_camera(instance.data["panel"], preset["camera"])
                )

                self._capture(preset)

        # Restoring viewport options.
        if viewport_defaults:
            cmds.modelEditor(
                instance.data["panel"], edit=True, **viewport_defaults
            )

        try:
            cmds.setAttr(
                "{}.panZoomEnabled".format(preset["camera"]), pan_zoom)
        except RuntimeError:
            self.log.warning("Cannot restore Pan/Zoom settings.")

        collected_files = os.listdir(stagingdir)
        patterns = [clique.PATTERNS["frames"]]
        collections, remainder = clique.assemble(collected_files,
                                                 minimum_items=1,
                                                 patterns=patterns)

        filename = preset.get("filename", "%TEMP%")
        self.log.debug("filename {}".format(filename))
        frame_collection = None
        for collection in collections:
            filebase = collection.format("{head}").rstrip(".")
            self.log.debug("collection head {}".format(filebase))
            if filebase in filename:
                frame_collection = collection
                self.log.info(
                    "we found collection of interest {}".format(
                        str(frame_collection)))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        # Add camera node name to representation data
        camera_node_name = cmds.listRelatives(camera, parent=True)[0]

        collected_files = list(frame_collection)
        # single frame file shouldn't be in list, only as a string
        if len(collected_files) == 1:
            collected_files = collected_files[0]

        representation = {
            "name": capture_preset["Codec"]["compression"],
            "ext": capture_preset["Codec"]["compression"],
            "files": collected_files,
            "stagingDir": stagingdir,
            "frameStart": start,
            "frameEnd": end,
            "fps": fps,
            "tags": tags,
            "camera_name": camera_node_name
        }
        instance.data["representations"].append(representation)
