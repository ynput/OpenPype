import os
import json
import contextlib
import clique
import capture

from pype.hosts.maya import lib
import pype.api

from maya import cmds
import pymel.core as pm


class ExtractPlayblast(pype.api.Extractor):
    """Extract viewport playblast.

    Takes review camera and creates review Quicktime video based on viewport
    capture.

    """

    label = "Extract Playblast"
    hosts = ["maya"]
    families = ["review"]
    optional = True

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
        capture_preset = instance.context.data.get(
            'presets', {}).get('maya', {}).get('capture')

        try:
            preset = lib.load_capture_preset(data=capture_preset)
        except Exception as exc:
            self.log.error(
                'Error loading capture presets: {}'.format(str(exc)))
            preset = {}
        self.log.info('Using viewport preset: {}'.format(preset))

        preset['camera'] = camera
        preset['format'] = "image"
        preset['quality'] = 95
        preset['compression'] = "png"
        preset['start_frame'] = start
        preset['end_frame'] = end
        camera_option = preset.get("camera_option", {})
        camera_option["depthOfField"] = cmds.getAttr(
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

        with maintained_time():
            filename = preset.get("filename", "%TEMP%")

            # Force viewer to False in call to capture because we have our own
            # viewer opening call to allow a signal to trigger between
            # playblast and viewer
            preset['viewer'] = False

            self.log.info(
                "Capturing with preset:\n{}".format(
                    json.dumps(preset, indent=4, sort_keys=True)
                )
            )
            path = capture.capture(**preset)

        # Restore panel camera.
        cmds.modelPanel(model_panel, edit=True, camera=panel_camera)

        collected_files = os.listdir(stagingdir)
        collections, remainder = clique.assemble(collected_files)

        self.log.debug("filename {}".format(filename))
        frame_collection = None
        for collection in collections:
            filebase = collection.format('{head}').rstrip(".")
            self.log.debug("collection head {}".format(filebase))
            if filebase in filename:
                frame_collection = collection
                self.log.info(
                    "We found collection of interest {}".format(
                        str(frame_collection)
                    )
                )

        if "representations" not in instance.data:
            instance.data["representations"] = []

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        # Add camera node name to representation data
        camera_node_name = pm.ls(camera)[0].getTransform().name()

        representation = {
            'name': 'png',
            'ext': 'png',
            'files': list(frame_collection),
            "stagingDir": stagingdir,
            "frameStart": start,
            "frameEnd": end,
            'fps': fps,
            'preview': True,
            'tags': tags,
            'camera_name': camera_node_name
        }
        instance.data["representations"].append(representation)


@contextlib.contextmanager
def maintained_time():
    ct = cmds.currentTime(query=True)
    try:
        yield
    finally:
        cmds.currentTime(ct, edit=True)
