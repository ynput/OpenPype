import os
import tempfile
import pyblish.api
import openpype.api
from openpype.lib import (
    get_ffmpeg_tool_path,
    get_ffprobe_streams,
    path_to_subprocess_arg,
)


class ExtractThumbnailSP(pyblish.api.InstancePlugin):
    """Extract jpeg thumbnail from component input from standalone publisher

    Uses jpeg file from component if possible (when single or multiple jpegs
    are loaded to component selected as thumbnail) otherwise extracts from
    input file/s single jpeg to temp.
    """

    label = "Extract Thumbnail SP"
    hosts = ["standalonepublisher"]
    order = pyblish.api.ExtractorOrder

    # Presetable attribute
    ffmpeg_args = None

    def process(self, instance):
        repres = instance.data.get('representations')
        if not repres:
            return

        thumbnail_repre = None
        for repre in repres:
            if repre.get("thumbnail"):
                thumbnail_repre = repre
                break

        if not thumbnail_repre:
            return

        thumbnail_repre.pop("thumbnail")
        files = thumbnail_repre.get("files")
        if not files:
            return

        if isinstance(files, list):
            first_filename = str(files[0])
        else:
            first_filename = files

        staging_dir = None

        # Convert to jpeg if not yet
        full_input_path = os.path.join(
            thumbnail_repre["stagingDir"], first_filename
        )
        self.log.info("input {}".format(full_input_path))
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            full_thumbnail_path = tmp.name

        self.log.info("output {}".format(full_thumbnail_path))

        instance.context.data["cleanupFullPaths"].append(full_thumbnail_path)

        ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")

        ffmpeg_args = self.ffmpeg_args or {}

        jpeg_items = [
            path_to_subprocess_arg(ffmpeg_path),
            # override file if already exists
            "-y"
        ]

        # add input filters from peresets
        jpeg_items.extend(ffmpeg_args.get("input") or [])
        # input file
        jpeg_items.extend([
            "-i", path_to_subprocess_arg(full_input_path),
            # extract only single file
            "-frames:v", "1",
            # Add black background for transparent images
            "-filter_complex", (
                "\"color=black,format=rgb24[c]"
                ";[c][0]scale2ref[c][i]"
                ";[c][i]overlay=format=auto:shortest=1,setsar=1\""
            ),
        ])

        jpeg_items.extend(ffmpeg_args.get("output") or [])

        # output file
        jpeg_items.append(path_to_subprocess_arg(full_thumbnail_path))

        subprocess_jpeg = " ".join(jpeg_items)

        # run subprocess
        self.log.debug("Executing: {}".format(subprocess_jpeg))
        openpype.api.run_subprocess(
            subprocess_jpeg, shell=True, logger=self.log
        )

        # remove thumbnail key from origin repre
        streams = get_ffprobe_streams(full_thumbnail_path)
        width = height = None
        for stream in streams:
            if "width" in stream and "height" in stream:
                width = stream["width"]
                height = stream["height"]
                break

        staging_dir, filename = os.path.split(full_thumbnail_path)

        # create new thumbnail representation
        representation = {
            'name': 'thumbnail',
            'ext': 'jpg',
            'files': filename,
            "stagingDir": staging_dir,
            "tags": ["thumbnail", "delete"],
        }
        if width and height:
            representation["width"] = width
            representation["height"] = height

        self.log.info(f"New representation {representation}")
        instance.data["representations"].append(representation)
