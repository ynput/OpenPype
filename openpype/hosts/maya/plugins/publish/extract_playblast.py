import os

import clique

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib

from maya import cmds


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

    def process(self, instance):
        self.log.debug("Extracting playblast..")

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

        self.log.debug("start: {}, end: {}".format(start, end))
        task_data = instance.data["anatomyData"].get("task", {})
        capture_preset = lib.get_capture_preset(
            task_data.get("name"),
            task_data.get("type"),
            instance.data["subset"],
            instance.context.data["project_settings"],
            self.log
        )
        stagingdir = self.staging_dir(instance)
        filename = "{0}".format(instance.name)
        path = os.path.join(stagingdir, filename)
        self.log.debug("Outputting images to %s" % path)
        # get cameras
        camera = instance.data["review_camera"]
        preset = lib.generate_capture_preset(
            instance, camera, path,
            start=start, end=end,
            capture_preset=capture_preset)
        path = lib.render_capture_preset(preset)

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
                self.log.debug(
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
            "frameStart": int(start),
            "frameEnd": int(end),
            "fps": fps,
            "tags": tags,
            "camera_name": camera_node_name
        }
        instance.data["representations"].append(representation)
