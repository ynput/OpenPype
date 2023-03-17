import os
import json

import clique
import capture

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib

from maya import cmds
import pymel.core as pm


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
        camera = instance.data['review_camera']

        preset = lib.load_capture_preset(data=self.capture_preset)
        # Grab capture presets from the project settings
        capture_presets = self.capture_preset
        # Set resolution variables from capture presets
        width_preset = capture_presets["Resolution"]["width"]
        height_preset = capture_presets["Resolution"]["height"]
        # Set resolution variables from asset values
        asset_data = instance.data["assetEntity"]["data"]
        asset_width = asset_data.get("resolutionWidth")
        asset_height = asset_data.get("resolutionHeight")
        review_instance_width = instance.data.get("review_width")
        review_instance_height = instance.data.get("review_height")
        preset['camera'] = camera

        # Tests if project resolution is set,
        # if it is a value other than zero, that value is
        # used, if not then the asset resolution is
        # used
        if review_instance_width and review_instance_height:
            preset['width'] = review_instance_width
            preset['height'] = review_instance_height
        elif width_preset and height_preset:
            preset['width'] = width_preset
            preset['height'] = height_preset
        elif asset_width and asset_height:
            preset['width'] = asset_width
            preset['height'] = asset_height
        preset['start_frame'] = start
        preset['end_frame'] = end

        # Enforce persisting camera depth of field
        camera_options = preset.setdefault("camera_options", {})
        camera_options["depthOfField"] = cmds.getAttr(
            "{0}.depthOfField".format(camera))

        stagingdir = self.staging_dir(instance)
        filename = "{0}".format(instance.name)
        path = os.path.join(stagingdir, filename)

        self.log.info("Outputting images to %s" % path)

        preset['filename'] = path
        preset['overwrite'] = True

        pm.refresh(f=True)

        refreshFrameInt = int(pm.playbackOptions(q=True, minTime=True))
        pm.currentTime(refreshFrameInt - 1, edit=True)
        pm.currentTime(refreshFrameInt, edit=True)

        # Override transparency if requested.
        transparency = instance.data.get("transparency", 0)
        if transparency != 0:
            preset["viewport2_options"]["transparencyAlgorithm"] = transparency

        # Isolate view is requested by having objects in the set besides a
        # camera.
        if preset.pop("isolate_view", False) and instance.data.get("isolate"):
            preset["isolate"] = instance.data["setMembers"]

        # Show/Hide image planes on request.
        image_plane = instance.data.get("imagePlane", True)
        if "viewport_options" in preset:
            preset["viewport_options"]["imagePlane"] = image_plane
        else:
            preset["viewport_options"] = {"imagePlane": image_plane}

        # Image planes do not update the file sequence unless the active panel
        # is viewing through the camera.
        model_panel = instance.context.data.get("model_panel")
        if not model_panel:
            model_panels = cmds.getPanel(type="modelPanel")
            visible_panels = cmds.getPanel(visiblePanels=True)
            model_panel = list(
                set(visible_panels) - (set(visible_panels) - set(model_panels))
            )[0]
            instance.context.data["model_panel"] = model_panel

        panel_camera = instance.context.data.get("panel_camera")
        if not panel_camera:
            panel_camera = capture.parse_view(model_panel)["camera"]
            instance.context.data["panel_camera"] = panel_camera

        cmds.modelPanel(model_panel, edit=True, camera=preset["camera"])

        # Disable Pan/Zoom.
        pan_zoom = cmds.getAttr("{}.panZoomEnabled".format(preset["camera"]))
        cmds.setAttr("{}.panZoomEnabled".format(preset["camera"]), False)

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
            capture_presets['Viewport Options']['override_viewport_options']
        )
        with lib.maintained_time():
            filename = preset.get("filename", "%TEMP%")

            # Force viewer to False in call to capture because we have our own
            # viewer opening call to allow a signal to trigger between
            # playblast and viewer
            preset['viewer'] = False

            # Update preset with current panel setting
            # if override_viewport_options is turned off
            if not override_viewport_options:
                panel_preset = capture.parse_view(instance.data["panel"])
                panel_preset.pop("camera")
                preset.update(panel_preset)

            self.log.info(
                "Using preset:\n{}".format(
                    json.dumps(preset, sort_keys=True, indent=4)
                )
            )

            path = capture.capture(log=self.log, **preset)

        # Restoring viewport options.
        if viewport_defaults:
            cmds.modelEditor(
                instance.data["panel"], edit=True, **viewport_defaults
            )

        cmds.setAttr("{}.panZoomEnabled".format(preset["camera"]), pan_zoom)

        # Restore panel camera.
        cmds.modelPanel(model_panel, edit=True, camera=panel_camera)

        self.log.debug("playblast path  {}".format(path))

        collected_files = os.listdir(stagingdir)
        patterns = [clique.PATTERNS["frames"]]
        collections, remainder = clique.assemble(collected_files,
                                                 minimum_items=1,
                                                 patterns=patterns)

        self.log.debug("filename {}".format(filename))
        frame_collection = None
        for collection in collections:
            filebase = collection.format('{head}').rstrip(".")
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
        camera_node_name = pm.ls(camera)[0].getTransform().name()

        collected_files = list(frame_collection)
        # single frame file shouldn't be in list, only as a string
        if len(collected_files) == 1:
            collected_files = collected_files[0]

        representation = {
            'name': 'png',
            'ext': 'png',
            'files': collected_files,
            "stagingDir": stagingdir,
            "frameStart": start,
            "frameEnd": end,
            'fps': fps,
            'preview': True,
            'tags': tags,
            'camera_name': camera_node_name
        }
        instance.data["representations"].append(representation)
