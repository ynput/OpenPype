import os
import clique

import bpy

import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.blender.api import capture
from openpype.hosts.blender.api.lib import maintained_time


class ExtractPlayblast(publish.Extractor, publish.OptionalPyblishPluginMixin):
    """
    Extract viewport playblast.

    Takes review camera and creates review Quicktime video based on viewport
    capture.
    """

    label = "Extract Playblast"
    hosts = ["blender"]
    families = ["review"]
    optional = True
    order = pyblish.api.ExtractorOrder + 0.01

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # get scene fps
        fps = instance.data.get("fps")
        if fps is None:
            fps = bpy.context.scene.render.fps
            instance.data["fps"] = fps

        self.log.debug(f"fps: {fps}")

        # If start and end frames cannot be determined,
        # get them from Blender timeline.
        start = instance.data.get("frameStart", bpy.context.scene.frame_start)
        end = instance.data.get("frameEnd", bpy.context.scene.frame_end)

        self.log.debug(f"start: {start}, end: {end}")
        assert end > start, "Invalid time range !"

        # get cameras
        camera = instance.data("review_camera", None)

        # get isolate objects list
        isolate = instance.data("isolate", None)

        # get output path
        stagingdir = self.staging_dir(instance)
        asset_name = instance.data["assetEntity"]["name"]
        subset = instance.data["subset"]
        filename = f"{asset_name}_{subset}"

        path = os.path.join(stagingdir, filename)

        self.log.debug(f"Outputting images to {path}")

        project_settings = instance.context.data["project_settings"]["blender"]
        presets = project_settings["publish"]["ExtractPlayblast"]["presets"]
        preset = presets.get("default")
        preset.update({
            "camera": camera,
            "start_frame": start,
            "end_frame": end,
            "filename": path,
            "overwrite": True,
            "isolate": isolate,
        })
        preset.setdefault(
            "image_settings",
            {
                "file_format": "PNG",
                "color_mode": "RGB",
                "color_depth": "8",
                "compression": 15,
            },
        )

        with maintained_time():
            path = capture(**preset)

        self.log.debug(f"playblast path {path}")

        collected_files = os.listdir(stagingdir)
        collections, remainder = clique.assemble(
            collected_files,
            patterns=[f"{filename}\\.{clique.DIGITS_PATTERN}\\.png$"],
        )

        if len(collections) > 1:
            raise RuntimeError(
                f"More than one collection found in stagingdir: {stagingdir}"
            )
        elif len(collections) == 0:
            raise RuntimeError(
                f"No collection found in stagingdir: {stagingdir}"
            )

        frame_collection = collections[0]

        self.log.debug(f"Found collection of interest {frame_collection}")

        instance.data.setdefault("representations", [])

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        representation = {
            "name": "png",
            "ext": "png",
            "files": list(frame_collection),
            "stagingDir": stagingdir,
            "frameStart": start,
            "frameEnd": end,
            "fps": fps,
            "tags": tags,
            "camera_name": camera
        }
        instance.data["representations"].append(representation)
