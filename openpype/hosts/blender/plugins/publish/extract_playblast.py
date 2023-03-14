import os
import clique

import bpy

import pyblish.api

from openpype.hosts.blender.api import capture
from openpype.hosts.blender.api.lib import maintained_time
from openpype.pipeline.publish.publish_plugins import Extractor


class ExtractPlayblast(Extractor):
    """Extract viewport playblast.

    Takes review camera and creates review Quicktime video based on viewport
    capture.

    """

    label = "Extract Playblast"
    hosts = ["blender"]
    families = ["review"]
    optional = True
    order = pyblish.api.ExtractorOrder + 0.01

    def process(self, instance):
        self.log.info("Extracting capture..")

        # get scene fps
        fps = instance.data.get("fps")
        if fps is None:
            fps = bpy.context.scene.render.fps
            instance.data["fps"] = fps

        self.log.info(f"fps: {fps}")

        # If start and end frames cannot be determined,
        # get them from Blender timeline.
        start = instance.data.get("frameStart", bpy.context.scene.frame_start)
        end = instance.data.get("frameEnd", bpy.context.scene.frame_end)

        self.log.info(f"start: {start}, end: {end}")

        # get cameras
        camera = instance.data("review_camera", None)

        # get isolate objects list
        isolate = instance.data("isolate", None)

        # get output path
        stagingdir = self.staging_dir(instance)
        filename = instance.name
        path = os.path.join(stagingdir, filename)

        self.log.info(f"Outputting images to {path}")

        family = instance.data.get("family")
        project_settings = instance.context.data["project_settings"]["blender"]
        presets = project_settings["publish"]["ExtractPlayblast"]["presets"]
        preset = presets.get(family, presets.get("default", {}))
        preset.update(
            {
                "camera": camera,
                "frame_start": start,
                "frame_end": end,
                "filepath": path,
                "overwrite": True,
                "isolate": isolate,
            }
        )
        preset.setdefault(
            "image_settings",
            {
                "file_format": "PNG",
                "color_mode": "RGB",
                "color_depth": "8",
                "compression": 15,
            },
        )

        # Keep current display shading
        # Catch source window because Win changes focus
        screen = bpy.context.window_manager.windows[0].screen
        current_area = next(
            (a for a in screen.areas if a.type == "VIEW_3D"), None
        )
        shading_type = (
            current_area.spaces[0].shading.type if current_area else "SOLID"
        )
        preset.setdefault("display_options", {})
        preset["display_options"].setdefault(
            "shading", {"type": shading_type}
        )
        preset["display_options"].setdefault(
            "overlay", {"show_overlays": False}
        )

        with maintained_time():
            path = capture(**preset)

        self.log.debug(f"playblast path {path}")

        # if only one frame
        if end == start:
            files = next(
                (
                    frame for frame in os.listdir(stagingdir)
                    if frame.endswith(".png")
                ),
                None
            )
            if not files:
                raise RuntimeError(
                    f"No frame found in stagingdir: {stagingdir}"
                )
        else:
            collected_files = os.listdir(stagingdir)
            collections, _ = clique.assemble(
                collected_files,
                patterns=[f"{filename}\\.{clique.DIGITS_PATTERN}\\.png$"],
            )

            if len(collections) > 1:
                raise RuntimeError(
                    "More than one collection found"
                    f"in stagingdir: {stagingdir}"
                )
            elif len(collections) == 0:
                raise RuntimeError(
                    f"No collection found in stagingdir: {stagingdir}"
                )

            frame_collection = collections[0]
            self.log.info(
                f"We found collection of interest {frame_collection}"
            )
            files = list(frame_collection)

        instance.data.setdefault("representations", [])

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        representation = {
            "name": "png",
            "ext": "png",
            "files": files,
            "stagingDir": stagingdir,
            "frameStart": start,
            "frameEnd": end,
            "fps": fps,
            "preview": True,
            "tags": tags,
            "camera_name": camera,
        }
        instance.data["representations"].append(representation)
