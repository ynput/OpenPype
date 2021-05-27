import os
import re

import pyblish.api
import pype.api
import pype.lib
from pype.lib import should_decompress, \
    get_decompress_dir, decompress
import shutil


class ExtractJpegEXR(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Jpeg EXR"
    hosts = ["shell", "fusion"]
    order = pyblish.api.ExtractorOrder
    families = ["imagesequence", "render", "render2d", "source"]
    enabled = False

    alpha_exts = ["exr", "png", "dpx"]
    color_regex = re.compile(r"^#[a-fA-F0-9]{6}$")

    # presetable attribute
    use_bg_color = True
    ffmpeg_args = None

    def process(self, instance):
        self.log.info("subset {}".format(instance.data['subset']))
        if 'crypto' in instance.data['subset']:
            return

        do_decompress = False
        # ffmpeg doesn't support multipart exrs, use oiiotool if available
        if instance.data.get("multipartExr") is True:
            return

        # Skip review when requested.
        if not instance.data.get("review", True):
            return

        # get representation and loop them
        representations = instance.data["representations"]

        # filter out mov and img sequences
        representations_new = representations[:]

        for repre in representations:
            tags = repre.get("tags", [])
            self.log.debug(repre)
            valid = 'review' in tags or "thumb-nuke" in tags
            if not valid:
                continue

            if not isinstance(repre['files'], (list, tuple)):
                input_file = repre['files']
            else:
                input_file = repre['files'][0]

            stagingdir = os.path.normpath(repre.get("stagingDir"))

            # input_file = (
            #     collections[0].format('{head}{padding}{tail}') % start
            # )
            full_input_path = os.path.join(stagingdir, input_file)
            self.log.info("input {}".format(full_input_path))

            decompressed_dir = ''
            do_decompress = should_decompress(full_input_path)
            if do_decompress:
                decompressed_dir = get_decompress_dir()

                decompress(
                    decompressed_dir,
                    full_input_path)
                # input path changed, 'decompressed' added
                full_input_path = os.path.join(
                    decompressed_dir,
                    input_file)

            filename = os.path.splitext(input_file)[0]
            if not filename.endswith('.'):
                filename += "."
            jpeg_file = filename + "jpg"
            full_output_path = os.path.join(stagingdir, jpeg_file)

            self.log.info("output {}".format(full_output_path))

            ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")
            ffmpeg_args = self.ffmpeg_args or {}

            jpeg_items = []
            jpeg_items.append("\"{}\"".format(ffmpeg_path))
            # override file if already exists
            jpeg_items.append("-y")
            # use same input args like with mov
            jpeg_items.extend(ffmpeg_args.get("input") or [])
            # input file
            jpeg_items.append("-i \"{}\"".format(full_input_path))
            # output arguments from presets
            output_args = self._prepare_output_args(
                ffmpeg_args.get("output"), full_input_path, instance
            )
            if output_args:
                jpeg_items.extend(output_args)

            # If its a movie file, we just want one frame.
            if repre["ext"] == "mov":
                jpeg_items.append("-vframes 1")

            # output file
            jpeg_items.append("\"{}\"".format(full_output_path))

            subprocess_jpeg = " ".join(jpeg_items)

            # run subprocess
            self.log.debug("{}".format(subprocess_jpeg))
            try:  # temporary until oiiotool is supported cross platform
                pype.api.subprocess(subprocess_jpeg, shell=True)
            except RuntimeError as exp:
                if "Compression" in str(exp):
                    self.log.debug("Unsupported compression on input files. " +
                                   "Skipping!!!")
                    return
                raise

            if "representations" not in instance.data:
                instance.data["representations"] = []

            representation = {
                'name': 'thumbnail',
                'ext': 'jpg',
                'files': jpeg_file,
                "stagingDir": stagingdir,
                "thumbnail": True,
                "tags": ['thumbnail']
            }

            # adding representation
            self.log.debug("Adding: {}".format(representation))
            representations_new.append(representation)

            if do_decompress and os.path.exists(decompressed_dir):
                shutil.rmtree(decompressed_dir)

        instance.data["representations"] = representations_new

    def _prepare_output_args(self, output_args, full_input_path, instance):
        output_args = output_args or []
        ext = os.path.splitext(full_input_path)[1].replace(".", "")
        bg_color = (
            instance.context.data["presets"]
            .get("tools", {})
            .get("extract_colors", {})
            .get("bg_color")
        )
        if (
            not bg_color
            or ext not in self.alpha_exts
            or not self.use_bg_color
        ):
            return output_args

        if not self.color_regex.match(bg_color):
            self.log.warning((
                "Background color set in presets \"{}\" has invalid format."
            ).format(bg_color))
            return output_args

        video_args_dentifiers = ["-vf", "-filter:v"]
        video_filters = []
        for idx, arg in reversed(tuple(enumerate(output_args))):
            for identifier in video_args_dentifiers:
                if identifier in arg:
                    output_args.pop(idx)
                    arg = arg.replace(identifier, "").strip()
                    video_filters.append(arg)

        video_filters.extend([
            "split=2[bg][fg]",
            "[bg]drawbox=c={}:replace=1:t=fill[bg]".format(bg_color),
            "[bg][fg]overlay=format=auto"
        ])

        output_args.append(
            "-filter:v {}".format(",".join(video_filters))
        )
        return output_args
