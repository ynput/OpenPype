import copy
import os
import subprocess
import tempfile
import re

import pyblish.api
from openpype.lib import (
    get_ffmpeg_tool_args,
    get_ffprobe_data,

    is_oiio_supported,
    get_rescaled_command_arguments,

    path_to_subprocess_arg,
    run_subprocess,
)
from openpype.lib.transcoding import (
    convert_colorspace,
    VIDEO_EXTENSIONS,
)


class ExtractThumbnail(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Thumbnail"
    order = pyblish.api.ExtractorOrder + 0.49
    families = [
        "imagesequence", "render", "render2d", "prerender",
        "source", "clip", "take", "online", "image"
    ]
    hosts = [
        "shell",
        "fusion",
        "resolve",
        "traypublisher",
        "substancepainter",
        "nuke",
        "aftereffects"
    ]
    enabled = False

    integrate_thumbnail = False
    target_size = {
        "type": "resize",
        "width": 1920,
        "height": 1080
    }
    background_color = None
    duration_split = 0.5
    # attribute presets from settings
    oiiotool_defaults = None
    ffmpeg_args = None
    subsets = []
    product_names = []

    def process(self, instance):
        # run main process
        self._main_process(instance)

        # Make sure cleanup happens to representations which are having both
        # tags `delete` and `need_thumbnail`
        for repre in tuple(instance.data.get("representations", [])):
            tags = repre.get("tags") or []
            # skip representations which are going to be published on farm
            if "publish_on_farm" in tags:
                continue
            if (
                "delete" in tags
                and "need_thumbnail" in tags
            ):
                self.log.debug(
                    "Removing representation: {}".format(repre)
                )
                instance.data["representations"].remove(repre)

    def _main_process(self, instance):
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

        # We only want to process the subsets needed from settings.
        def validate_string_against_patterns(input_str, patterns):
            for pattern in patterns:
                if re.match(pattern, input_str):
                    return True
            return False

        product_names = self.subsets + self.product_names
        if product_names:
            result = validate_string_against_patterns(
                instance.data["subset"], product_names
            )
            if not result:
                self.log.debug(
                    "Subset \"{}\" did not match any valid subsets: {}".format(
                        instance.data["subset"], product_names
                    )
                )
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
                # this will also work with ffmpeg fallback conversion in case
                # oiio is not supported
                repre_extension = os.path.splitext(repre_files)[1]
                if repre_extension in VIDEO_EXTENSIONS:
                    video_file_path = os.path.join(
                        src_staging, repre_files
                    )
                    file_path = self._create_frame_from_video(
                        video_file_path,
                        dst_staging
                    )
                    if file_path:
                        src_staging, input_file = os.path.split(file_path)
                else:
                    # if it is not video file then just use first file
                    input_file = repre_files
            else:
                repre_files_thumb = copy.deepcopy(repre_files)
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
                thumbnail_created = self._create_thumbnail_oiio(
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

                thumbnail_created = self._create_thumbnail_ffmpeg(
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
                self.log.debug(
                    "Adding thumbnail path to instance data: {}".format(
                        full_output_path
                    )
                )
                instance.data["thumbnailPath"] = full_output_path

            new_repre_tags = ["thumbnail"]
            # for workflows which needs to have thumbnails published as
            # separate representations `delete` tag should not be added
            if not self.integrate_thumbnail:
                new_repre_tags.append("delete")

            new_repre = {
                "name": repre_name,
                "ext": "jpg",
                "files": jpeg_file,
                "stagingDir": dst_staging,
                "thumbnail": True,
                "tags": new_repre_tags,
                # If source image is jpg then there can be clash when
                # integrating to making the output name explicit.
                "outputName": "thumbnail"
            }

            # adding representation
            instance.data["representations"].append(new_repre)

            if explicit_repres:
                # this key will then align assetVersion ftrack thumbnail sync
                new_repre["outputName"] = (
                    repre.get("outputName") or repre["name"])
                self.log.debug(
                    "Adding explicit thumbnail representation: {}".format(
                        new_repre))
            else:
                self.log.debug(
                    "Adding thumbnail representation: {}".format(new_repre)
                )
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
        #   one instance and representations are tagged for thumbnail.
        # First check if any of the representations have
        # `need_thumbnail` in tags and add them to filtered_repres
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
            "Representations: {}".format(need_thumb_repres)
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

    def _create_thumbnail_oiio(
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
        resolution_arg = self._get_resolution_arg("oiiotool", src_path)

        repre_display = colorspace_data.get("display")
        repre_view = colorspace_data.get("view")
        oiio_default_type = None
        oiio_default_display = None
        oiio_default_view = None
        oiio_default_colorspace = None
        # first look into representation colorspaceData, perhaps it has
        #   display and view
        if all([repre_display, repre_view]):
            self.log.info(
                "Using Display & View from "
                "representation: '{} ({})'".format(
                    repre_view,
                    repre_display
                )
            )
        # if representation doesn't have display and view then use
        #   oiiotool_defaults
        elif self.oiiotool_defaults:
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
                display=repre_display or oiio_default_display,
                view=repre_view or oiio_default_view,
                target_colorspace=oiio_default_colorspace,
                additional_command_args=resolution_arg,
                logger=self.log,
            )
        except Exception:
            self.log.warning(
                "Failed to create thumbnail using oiiotool",
                exc_info=True
            )
            return False

        return True

    def _create_thumbnail_ffmpeg(self, src_path, dst_path):
        self.log.debug("Extracting thumbnail with FFMPEG: {}".format(dst_path))
        resolution_arg = self._get_resolution_arg("ffmpeg", src_path)
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

        if resolution_arg:
            jpeg_items.extend(resolution_arg)

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

    def _create_frame_from_video(self, video_file_path, output_dir):
        """Convert video file to one frame image via ffmpeg"""
        # create output file path
        base_name = os.path.basename(video_file_path)
        filename = os.path.splitext(base_name)[0]
        output_thumb_file_path = os.path.join(
            output_dir, "{}.png".format(filename))

        # Set video input attributes
        max_int = str(2147483647)
        video_data = get_ffprobe_data(video_file_path, logger=self.log)
        # Use duration of the individual streams since it is returned with
        # higher decimal precision than 'format.duration'. We need this
        # more precise value for calculating the correct amount of frames
        # for higher FPS ranges or decimal ranges, e.g. 29.97 FPS
        duration = max(
            float(stream.get("duration", 0))
            for stream in video_data["streams"]
            if stream.get("codec_type") == "video"
        )

        cmd_args = [
            "-y",
            "-ss", str(duration * self.duration_split),
            "-i", video_file_path,
            "-analyzeduration", max_int,
            "-probesize", max_int,
            "-vframes", "1"
        ]

        # add output file path
        cmd_args.append(output_thumb_file_path)

        # create ffmpeg command
        cmd = get_ffmpeg_tool_args(
            "ffmpeg",
            *cmd_args
        )
        try:
            # run subprocess
            self.log.debug("Executing: {}".format(" ".join(cmd)))
            run_subprocess(cmd, logger=self.log)
            self.log.debug(
                "Thumbnail created: {}".format(output_thumb_file_path))
            return output_thumb_file_path
        except RuntimeError as error:
            self.log.warning(
                "Failed intermediate thumb source using ffmpeg: {}".format(
                    error)
            )
            return None

    def _get_resolution_arg(
        self,
        application,
        input_path,
    ):
        # get settings
        if self.target_size.get("type") == "source":
            return []

        target_width = self.target_size["width"]
        target_height = self.target_size["height"]

        # form arg string per application
        return get_rescaled_command_arguments(
            application,
            input_path,
            target_width,
            target_height,
            bg_color=self.background_color,
            log=self.log
        )
