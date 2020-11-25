import os

import pyblish.api
import pype.api
import pype.lib
from pype.plugins import lib as plugins_lib
import shutil


class ExtractJpegEXR(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Jpeg EXR"
    hosts = ["shell", "fusion"]
    order = pyblish.api.ExtractorOrder
    families = ["imagesequence", "render", "render2d", "source"]
    enabled = False

    # presetable attribute
    ffmpeg_args = None

    def process(self, instance):
        self.log.info("subset {}".format(instance.data['subset']))
        if 'crypto' in instance.data['subset']:
            return

        decompress = False
        # ffmpeg doesn't support multipart exrs, use oiiotool if available
        if instance.data.get("multipartExr") is True:
            if not plugins_lib.oiio_supported():
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
            decompress = plugins_lib.should_decompress(full_input_path)
            if decompress:
                decompressed_dir = plugins_lib.get_decompress_dir()

                plugins_lib.decompress(
                    decompressed_dir,
                    [full_input_path])
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
            jpeg_items.append("-i {}".format(full_input_path))
            # output arguments from presets
            jpeg_items.extend(ffmpeg_args.get("output") or [])

            # If its a movie file, we just want one frame.
            if repre["ext"] == "mov":
                jpeg_items.append("-vframes 1")

            # output file
            jpeg_items.append(full_output_path)

            subprocess_jpeg = " ".join(jpeg_items)

            # run subprocess
            self.log.debug("{}".format(subprocess_jpeg))
            pype.api.subprocess(subprocess_jpeg, shell=True)

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

            if decompress and os.path.exists(decompressed_dir):
                shutil.rmtree(decompressed_dir)

        instance.data["representations"] = representations_new
