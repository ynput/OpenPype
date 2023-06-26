import os
import tempfile

import pyblish.api
from openpype.lib import (
    get_ffmpeg_tool_path,
    get_oiio_tools_path,
    is_oiio_supported,

    run_subprocess,
    path_to_subprocess_arg,
)


class ExtractThumbnail(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Thumbnail"
    order = pyblish.api.ExtractorOrder
    families = [
        "imagesequence", "render", "render2d", "prerender",
        "source", "clip", "take", "online", "image"
    ]
    hosts = ["shell", "fusion", "resolve", "traypublisher", "substancepainter"]
    enabled = False

    # presetable attribute
    ffmpeg_args = None

    def process(self, instance):
        subset_name = instance.data["subset"]
        instance_repres = instance.data.get("representations")
        if not instance_repres:
            self.log.debug((
                "Instance {} does not have representations. Skipping"
            ).format(subset_name))
            return

        self.log.debug(
            "Processing instance with subset name {}".format(subset_name)
        )

        # Skip if instance have 'review' key in data set to 'False'
        if not self._is_review_instance(instance):
            self.log.info("Skipping - no review set on instance.")
            return

        # Check if already has thumbnail created
        if self._already_has_thumbnail(instance_repres):
            self.log.info("Thumbnail representation already present.")
            return

        # skip crypto passes.
        # TODO: This is just a quick fix and has its own side-effects - it is
        #       affecting every subset name with `crypto` in its name.
        #       This must be solved properly, maybe using tags on
        #       representation that can be determined much earlier and
        #       with better precision.
        if "crypto" in subset_name.lower():
            self.log.info("Skipping crypto passes.")
            return

        filtered_repres = self._get_filtered_repres(instance)
        if not filtered_repres:
            self.log.info((
                "Instance don't have representations"
                " that can be used as source for thumbnail. Skipping"
            ))
            return

        # Create temp directory for thumbnail
        # - this is to avoid "override" of source file
        dst_staging = tempfile.mkdtemp(prefix="pyblish_tmp_")
        self.log.debug(
            "Create temp directory {} for thumbnail".format(dst_staging)
        )
        # Store new staging to cleanup paths
        instance.context.data["cleanupFullPaths"].append(dst_staging)

        thumbnail_created = False
        oiio_supported = is_oiio_supported()
        for repre in filtered_repres:
            repre_files = repre["files"]
            if not isinstance(repre_files, (list, tuple)):
                input_file = repre_files
            else:
                file_index = int(float(len(repre_files)) * 0.5)
                input_file = repre_files[file_index]

            src_staging = os.path.normpath(repre["stagingDir"])
            full_input_path = os.path.join(src_staging, input_file)
            self.log.debug("input {}".format(full_input_path))
            filename = os.path.splitext(input_file)[0]
            jpeg_file = filename + "_thumb.jpg"
            full_output_path = os.path.join(dst_staging, jpeg_file)

            if oiio_supported:
                self.log.debug("Trying to convert with OIIO")
                # If the input can read by OIIO then use OIIO method for
                # conversion otherwise use ffmpeg
                thumbnail_created = self.create_thumbnail_oiio(
                    full_input_path, full_output_path
                )

            # Try to use FFMPEG if OIIO is not supported or for cases when
            #    oiiotool isn't available
            if not thumbnail_created:
                if oiio_supported:
                    self.log.info((
                        "Converting with FFMPEG because input"
                        " can't be read by OIIO."
                    ))

                thumbnail_created = self.create_thumbnail_ffmpeg(
                    full_input_path, full_output_path
                )

            # Skip representation and try next one if  wasn't created
            if not thumbnail_created:
                continue

            new_repre = {
                "name": "thumbnail",
                "ext": "jpg",
                "files": jpeg_file,
                "stagingDir": dst_staging,
                "thumbnail": True,
                "tags": ["thumbnail"]
            }

            # adding representation
            self.log.debug(
                "Adding thumbnail representation: {}".format(new_repre)
            )
            instance.data["representations"].append(new_repre)
            # There is no need to create more then one thumbnail
            break

        if not thumbnail_created:
            self.log.warning("Thumbanil has not been created.")

    def _is_review_instance(self, instance):
        # TODO: We should probably handle "not creating" of thumbnail
        #   other way then checking for "review" key on instance data?
        if instance.data.get("review", True):
            return True
        return False

    def _already_has_thumbnail(self, repres):
        for repre in repres:
            self.log.debug("repre {}".format(repre))
            if repre["name"] == "thumbnail":
                return True
        return False

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
        self.log.info("Extracting thumbnail {}".format(dst_path))
        oiio_tool_path = get_oiio_tools_path()
        oiio_cmd = [
            oiio_tool_path,
            "-a", src_path,
            "-o", dst_path
        ]
        self.log.debug("running: {}".format(" ".join(oiio_cmd)))
        try:
            run_subprocess(oiio_cmd, logger=self.log)
            return True
        except Exception:
            self.log.warning(
                "Failed to create thumbnail using oiiotool",
                exc_info=True
            )
            return False

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
        try:
            run_subprocess(
                subprocess_command, shell=True, logger=self.log
            )
            return True
        except Exception:
            self.log.warning(
                "Failed to create thubmnail using ffmpeg",
                exc_info=True
            )
            return False
