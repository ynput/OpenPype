import os

import pyblish.api
from openpype.lib import (
    get_ffmpeg_tool_path,
    get_oiio_tools_path,
    is_oiio_supported,

    run_subprocess,
    path_to_subprocess_arg,

    execute,
)


class ExtractThumbnail(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Thumbnail"
    order = pyblish.api.ExtractorOrder
    families = [
        "imagesequence", "render", "render2d",
        "source", "plate", "take"
    ]
    hosts = ["shell", "fusion", "resolve"]
    enabled = False

    # presetable attribute
    ffmpeg_args = None

    def process(self, instance):
        self.log.info("subset {}".format(instance.data['subset']))

        # skip crypto passes.
        # TODO: This is just a quick fix and has its own side-effects - it is
        #       affecting every subset name with `crypto` in its name.
        #       This must be solved properly, maybe using tags on
        #       representation that can be determined much earlier and
        #       with better precision.
        if 'crypto' in instance.data['subset'].lower():
            self.log.info("Skipping crypto passes.")
            return

        # Skip if review not set.
        if not instance.data.get("review", True):
            self.log.info("Skipping - no review set on instance.")
            return

        filtered_repres = self._get_filtered_repres(instance)
        for repre in filtered_repres:
            repre_files = repre["files"]
            if not isinstance(repre_files, (list, tuple)):
                input_file = repre_files
            else:
                file_index = int(float(len(repre_files)) * 0.5)
                input_file = repre_files[file_index]

            stagingdir = os.path.normpath(repre["stagingDir"])

            full_input_path = os.path.join(stagingdir, input_file)
            self.log.info("input {}".format(full_input_path))
            filename = os.path.splitext(input_file)[0]
            if not filename.endswith('.'):
                filename += "."
            jpeg_file = filename + "jpg"
            full_output_path = os.path.join(stagingdir, jpeg_file)

            thumbnail_created = False
            # Try to use FFMPEG if OIIO is not supported (for cases when
            # oiiotool isn't available)
            if not is_oiio_supported():
                thumbnail_created = self.create_thumbnail_ffmpeg(full_input_path, full_output_path) # noqa
            else:
                # Check if the file can be read by OIIO
                oiio_tool_path = get_oiio_tools_path()
                args = [
                    oiio_tool_path, "--info", "-i", full_output_path
                ]
                returncode = execute(args, silent=True)
                # If the input can read by OIIO then use OIIO method for
                # conversion otherwise use ffmpeg
                if returncode == 0:
                    self.log.info("Input can be read by OIIO, converting with oiiotool now.")
                    thumbnail_created = self.create_thumbnail_oiio(full_input_path, full_output_path) # noqa
                else:
                    self.log.info("Converting with FFMPEG because input can't be read by OIIO.")
                    thumbnail_created = self.create_thumbnail_ffmpeg(full_input_path, full_output_path) # noqa

            # Skip the rest of the process if the thumbnail wasn't created
            if not thumbnail_created:
                self.log.warning("Thumbanil has not been created.")
                return

            new_repre = {
                    "name": "thumbnail",
                    "ext": "jpg",
                    "files": jpeg_file,
                    "stagingDir": stagingdir,
                    "thumbnail": True,
                    "tags": ["thumbnail"]
                }

        # adding representation
        self.log.debug("Adding: {}".format(new_repre))
        instance.data["representations"].append(new_repre)

    def _get_filtered_repres(self, instance):
        filtered_repres = []
        src_repres = instance.data.get("representations") or []
        for repre in src_repres:
            self.log.debug(repre)
            tags = repre.get("tags") or []
            valid = "review" in tags or "thumb-nuke" in tags
            if not valid:
                continue

            if not repre.get("files"):
                self.log.info((
                    "Representation \"{}\" don't have files. Skipping"
                ).format(repre["name"]))
                continue

            filtered_repres.append(repre)
        return filtered_repres

    def create_thumbnail_oiio(self, src_path, dst_path):
        self.log.info("outputting {}".format(dst_path))
        oiio_tool_path = get_oiio_tools_path()
        oiio_cmd = [oiio_tool_path,
                    src_path, "-o",
                    dst_path
                    ]
        self.log.info(f"running: {oiio_cmd}")
        run_subprocess(oiio_cmd, logger=self.log)

    def create_thumbnail_ffmpeg(self, src_path, dst_path):
        self.log.info("outputting {}".format(dst_path))

        ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")
        ffmpeg_args = self.ffmpeg_args or {}

        jpeg_items = []
        jpeg_items.append(path_to_subprocess_arg(ffmpeg_path))
        # override file if already exists
        jpeg_items.append("-y")
        # flag for large file sizes
        max_int = 2147483647
        jpeg_items.append("-analyzeduration {}".format(max_int))
        jpeg_items.append("-probesize {}".format(max_int))
        # use same input args like with mov
        jpeg_items.extend(ffmpeg_args.get("input") or [])
        # input file
        jpeg_items.append("-i {}".format(
            path_to_subprocess_arg(src_path)
        ))
        # output arguments from presets
        jpeg_items.extend(ffmpeg_args.get("output") or [])
        # we just want one frame from movie files
        jpeg_items.append("-vframes 1")
        # output file
        jpeg_items.append(path_to_subprocess_arg(dst_path))
        subprocess_command = " ".join(jpeg_items)
        run_subprocess(
                subprocess_command, shell=True, logger=self.log
            )
