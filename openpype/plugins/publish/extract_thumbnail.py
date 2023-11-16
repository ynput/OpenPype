import copy
import os
import subprocess
import tempfile
from pprint import pformat

import pyblish.api
from openpype.lib import (
    get_ffmpeg_tool_args,
    get_ffprobe_data,
    is_oiio_supported,

    run_subprocess,
    path_to_subprocess_arg,
)
from openpype.lib.transcoding import (
    VIDEO_EXTENSIONS,
    convert_colorspace)

class ExtractThumbnail(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Thumbnail"
    order = pyblish.api.ExtractorOrder + 0.49
    families = [
        "imagesequence", "render", "render2d", "prerender",
        "source", "clip", "take", "online", "image"
    ]
    hosts = ["shell", "nuke", "fusion", "resolve", "traypublisher", "substancepainter"]
    enabled = False

    duration_split = 0.5
    oiiotool_defaults = None
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
            self.log.debug("Skipping - no review set on instance.")
            return

        # Check if already has thumbnail created
        if self._already_has_thumbnail(instance_repres):
            self.log.debug("Thumbnail representation already present.")
            return

        # skip crypto passes.
        # TODO: This is just a quick fix and has its own side-effects - it is
        #       affecting every subset name with `crypto` in its name.
        #       This must be solved properly, maybe using tags on
        #       representation that can be determined much earlier and
        #       with better precision.
        if "crypto" in subset_name.lower():
            self.log.debug("Skipping crypto passes.")
            return

        # first check for any explicitly marked representations for thumbnail
        explicit_repres = self._get_explicit_repres_for_thumbnail(instance)
        if explicit_repres:
            filtered_repres = explicit_repres
        else:
            filtered_repres = self._get_filtered_repres(instance)

        if not filtered_repres:
            self.log.info(
                "Instance doesn't have representations that can be used "
                "as source for thumbnail. Skipping thumbnail extraction."
            )
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
            src_staging = os.path.normpath(repre["stagingDir"])
            if not isinstance(repre_files, (list, tuple)):
                # convert any video file to frame so oiio doesn't need to
                # read video file (it is slow) and also we are having control
                # over which frame is used for thumbnail
                repre_extension = os.path.splitext(repre_files)[1]
                if repre_extension in VIDEO_EXTENSIONS:
                    video_file_path = os.path.join(
                        src_staging, repre_files
                    )
                    file_path = self._convert_video_to_frame(
                        video_file_path,
                        dst_staging
                    )
                    if file_path:
                        src_staging, input_file = os.path.split(file_path)
                else:
                    # if it is not video file then just use first file
                    input_file = repre_files
            else:
                repre_files_thumb = copy(repre_files)
                # exclude first frame if slate in representation tags
                if "slate-frame" in repre.get("tags", []):
                    repre_files_thumb = repre_files_thumb[1:]
                file_index = int(
                    float(len(repre_files_thumb)) * self.duration_split)
                input_file = repre_files[file_index]

            full_input_path = os.path.join(src_staging, input_file)
            self.log.debug("input {}".format(full_input_path))

            filename = os.path.splitext(input_file)[0]
            jpeg_file = filename + "_thumb.jpg"
            full_output_path = os.path.join(dst_staging, jpeg_file)
            colorspace_data = repre.get("colorspaceData")

            # only use OIIO if it is supported and representation has
            # colorspace data
            if oiio_supported and colorspace_data:
                self.log.debug(
                    "Trying to convert with OIIO "
                    "with colorspace data: {}".format(colorspace_data)
                )
                # If the input can read by OIIO then use OIIO method for
                # conversion otherwise use ffmpeg
                thumbnail_created = self.create_thumbnail_oiio(
                    full_input_path,
                    full_output_path,
                    colorspace_data
                )

            # Try to use FFMPEG if OIIO is not supported or for cases when
            #   oiiotool isn't available or representation is not having
            #   colorspace data
            if not thumbnail_created:
                if oiio_supported:
                    self.log.debug(
                        "Converting with FFMPEG because input"
                        " can't be read by OIIO."
                    )

                thumbnail_created = self.create_thumbnail_ffmpeg(
                    full_input_path, full_output_path
                )

            # Skip representation and try next one if  wasn't created
            if not thumbnail_created:
                continue

            if len(explicit_repres) > 1:
                repre_name = "thumbnail_{}".format(repre["outputName"])
            else:
                repre_name = "thumbnail"

            # add thumbnail path to instance data for integrator
            instance_thumb_path = instance.data.get("thumbnailPath")
            if (
                not instance_thumb_path
                or not os.path.isfile(instance_thumb_path)
            ):
                instance.data["thumbnailPath"] = full_output_path

            new_repre = {
                "name": repre_name,
                "ext": "jpg",
                "files": jpeg_file,
                "stagingDir": dst_staging,
                "thumbnail": True,
                "tags": ["thumbnail", "delete"]
            }

            # adding representation
            self.log.debug(
                "Adding thumbnail representation: {}".format(new_repre)
            )
            instance.data["representations"].append(new_repre)

            if explicit_repres:
                # this key will then align assetVersion ftrack thumbnail sync
                new_repre["outputName"] = repre["outputName"]
            else:
                # There is no need to create more then one thumbnail
                break

        if not thumbnail_created:
            self.log.warning("Thumbnail has not been created.")

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

    def _get_explicit_repres_for_thumbnail(self, instance):
        src_repres = instance.data.get("representations") or []
        # This is mainly for Nuke where we have multiple representations for
        #   one instance. We want to use only one representation for thumbnail
        # first check if any of the representations have
        # `need-thumbnail` in tags and add them to filtered_repres
        need_thumb_repres = [
            repre for repre in src_repres
            if "need_thumbnail" in repre.get("tags", [])
            if "publish_on_farm" not in repre.get("tags", [])
        ]
        if not need_thumb_repres:
            return []

        self.log.info(
            "Instance has representation with tag `need_thumbnail`. "
            "Using only this representations for thumbnail creation. "
        )
        self.log.debug(
            "Representations: {}".format(pformat(need_thumb_repres))
        )
        return need_thumb_repres

    def _get_filtered_repres(self, instance):
        filtered_repres = []
        src_repres = instance.data.get("representations") or []

        for repre in src_repres:
            self.log.debug(repre)
            tags = repre.get("tags") or []

            if "publish_on_farm" in tags:
                # only process representations with are going
                # to be published locally
                continue

            valid = "review" in tags or "thumb-nuke" in tags
            if not valid:
                continue

            if not repre.get("files"):
                self.log.debug((
                    "Representation \"{}\" doesn't have files. Skipping"
                ).format(repre["name"]))
                continue

            filtered_repres.append(repre)
        return filtered_repres

    def create_thumbnail_oiio(
        self,
        src_path,
        dst_path,
        colorspace_data,
    ):
        """Create thumbnail using OIIO tool oiiotool

        Args:
            src_path (str): path to source file
            dst_path (str): path to destination file
            colorspace_data (dict): colorspace data from representation
                keys:
                    colorspace (str)
                    config (dict)
                    display (Optional[str])
                    view (Optional[str])

        Returns:
            str: path to created thumbnail
        """
        self.log.info("Extracting thumbnail {}".format(dst_path))

        oiio_default_type = None
        oiio_default_display = None
        oiio_default_view = None
        oiio_default_colorspace = None
        self.log.debug(
            self.oiiotool_defaults
        )
        self.log.debug(self.ffmpeg_args)
        if self.oiiotool_defaults:
            oiio_default_type = self.oiiotool_defaults["type"]
            if "colorspace" in oiio_default_type:
                oiio_default_colorspace = self.oiiotool_defaults["colorspace"]
            else:
                oiio_default_display = self.oiiotool_defaults["display"]
                oiio_default_view = self.oiiotool_defaults["view"]
        try:
            convert_colorspace(
                src_path,
                dst_path,
                colorspace_data["config"]["path"],
                colorspace_data["colorspace"],
                display=colorspace_data.get("display") or oiio_default_display,
                view=colorspace_data.get("view") or oiio_default_view,
                target_colorspace=oiio_default_colorspace,
                additional_input_args=["-i:ch=R,G,B"],
                logger=self.log,
            )
        except Exception:
            self.log.warning(
                "Failed to create thumbnail using oiiotool",
                exc_info=True
            )
            return False

        return dst_path

    def create_thumbnail_ffmpeg(self, src_path, dst_path):
        self.log.debug("Extracting thumbnail with FFMPEG: {}".format(dst_path))

        ffmpeg_path_args = get_ffmpeg_tool_args("ffmpeg")
        ffmpeg_args = self.ffmpeg_args or {}

        jpeg_items = [
            subprocess.list2cmdline(ffmpeg_path_args)
        ]
        # flag for large file sizes
        max_int = 2147483647
        jpeg_items.extend([
            "-y",
            "-analyzeduration", str(max_int),
            "-probesize", str(max_int),
        ])
        # use same input args like with mov
        jpeg_items.extend(ffmpeg_args.get("input") or [])
        # input file
        jpeg_items.extend(["-i", path_to_subprocess_arg(src_path)])
        # output arguments from presets
        jpeg_items.extend(ffmpeg_args.get("output") or [])
        # we just want one frame from movie files
        jpeg_items.extend(["-vframes", "1"])
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
                "Failed to create thumbnail using ffmpeg",
                exc_info=True
            )
            return False

    def _convert_video_to_frame(self, video_file_path, output_dir):
        """Convert video file to one frame image via ffmpeg"""
        # create output file path
        base_name = os.path.basename(video_file_path)
        filename = os.path.splitext(base_name)[0]
        output_thumb_file_path = os.path.join(output_dir, "{}.png".format(filename))

        # Set video input attributes
        max_int = str(2147483647)
        video_data = get_ffprobe_data(video_file_path, logger=self.log)
        duration = float(video_data["format"]["duration"])

        # create ffmpeg command
        cmd = get_ffmpeg_tool_args(
            "ffmpeg",
            "-y",
            "-ss", str(duration * self.duration_split),
            "-i", video_file_path,
            "-analyzeduration", max_int,
            "-probesize", max_int,
            "-vframes", "1",
            output_thumb_file_path
        )
        try:
            # run subprocess
            self.log.debug("Executing: {}".format(" ".join(cmd)))
            run_subprocess(cmd, logger=self.log)
            self.log.debug("Thumbnail created: {}".format(output_thumb_file_path))
            return output_thumb_file_path
        except RuntimeError as error:
            self.log.warning(
                "Failed intermediate thumb source using ffmpeg: {}".format(
                    error)
            )
            return None
