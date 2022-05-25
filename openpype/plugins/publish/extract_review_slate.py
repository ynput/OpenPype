import os
from pprint import pformat
import re
import openpype.api
import pyblish
from openpype.lib import (
    path_to_subprocess_arg,
    get_ffmpeg_tool_path,
    get_ffprobe_data,
    get_ffprobe_streams,
    get_ffmpeg_codec_args,
    get_ffmpeg_format_args,
)


class ExtractReviewSlate(openpype.api.Extractor):
    """
    Will add slate frame at the start of the video files
    """

    label = "Review with Slate frame"
    order = pyblish.api.ExtractorOrder + 0.031
    families = ["slate", "review"]
    match = pyblish.api.Subset

    SUFFIX = "_slate"

    hosts = ["nuke", "shell"]
    optional = True

    def process(self, instance):
        inst_data = instance.data
        if "representations" not in inst_data:
            raise RuntimeError("Burnin needs already created mov to work on.")

        # get slates frame from upstream
        slates_data = inst_data.get("slateFrames")
        if not slates_data:
            # make it backward compatible and open for slates generator
            # premium plugin
            slates_data = {
                "*": inst_data["slateFrame"]
            }

        self.log.info("_ slates_data: {}".format(pformat(slates_data)))

        ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")

        if "reviewToWidth" in inst_data:
            use_legacy_code = True
        else:
            use_legacy_code = False

        pixel_aspect = inst_data.get("pixelAspect", 1)
        fps = inst_data.get("fps")

        for idx, repre in enumerate(inst_data["representations"]):
            self.log.debug("repre ({}): `{}`".format(idx + 1, repre))

            p_tags = repre.get("tags", [])
            if "slate-frame" not in p_tags:
                continue

            # get repre file
            stagingdir = repre["stagingDir"]
            input_file = "{0}".format(repre["files"])
            input_path = os.path.join(
                os.path.normpath(stagingdir), repre["files"])
            self.log.debug("__ input_path: {}".format(input_path))

            video_streams = get_ffprobe_streams(
                input_path, self.log
            )

            # get slate data
            slate_path = self._get_slate_path(input_file, slates_data)
            self.log.info("_ slate_path: {}".format(slate_path))

            slate_width, slate_height = self._get_slates_resolution(slate_path)

            # Try to find first stream with defined 'width' and 'height'
            # - this is to avoid order of streams where audio can be as first
            # - there may be a better way (checking `codec_type`?)
            input_width = None
            input_height = None
            for stream in video_streams:
                if "width" in stream and "height" in stream:
                    input_width = int(stream["width"])
                    input_height = int(stream["height"])
                    break

            # Raise exception of any stream didn't define input resolution
            if input_width is None:
                raise AssertionError((
                    "FFprobe couldn't read resolution from input file: \"{}\""
                ).format(input_path))

            # values are set in ExtractReview
            if use_legacy_code:
                to_width = inst_data["reviewToWidth"]
                to_height = inst_data["reviewToHeight"]
            else:
                to_width = input_width
                to_height = input_height

            self.log.debug("to_width: `{}`".format(to_width))
            self.log.debug("to_height: `{}`".format(to_height))

            # defining image ratios
            resolution_ratio = (
                (float(slate_width) * pixel_aspect) / slate_height
            )
            delivery_ratio = float(to_width) / float(to_height)
            self.log.debug("resolution_ratio: `{}`".format(resolution_ratio))
            self.log.debug("delivery_ratio: `{}`".format(delivery_ratio))

            # get scale factor
            scale_factor_by_height = float(to_height) / slate_height
            scale_factor_by_width = float(to_width) / (
                slate_width * pixel_aspect
            )

            # shorten two decimals long float number for testing conditions
            resolution_ratio_test = float("{:0.2f}".format(resolution_ratio))
            delivery_ratio_test = float("{:0.2f}".format(delivery_ratio))

            self.log.debug("__ scale_factor_by_width: `{}`".format(
                scale_factor_by_width
            ))
            self.log.debug("__ scale_factor_by_height: `{}`".format(
                scale_factor_by_height
            ))

            _remove_at_end = []

            ext = os.path.splitext(input_file)[1]
            output_file = input_file.replace(ext, "") + self.SUFFIX + ext

            _remove_at_end.append(input_path)

            output_path = os.path.join(
                os.path.normpath(stagingdir), output_file)
            self.log.debug("__ output_path: {}".format(output_path))

            input_args = []
            output_args = []

            # preset's input data
            if use_legacy_code:
                input_args.extend(repre["_profile"].get('input', []))
            else:
                input_args.extend(repre["outputDef"].get('input', []))
            input_args.append("-loop 1 -i {}".format(
                path_to_subprocess_arg(slate_path)
            ))
            input_args.extend([
                "-r {}".format(fps),
                "-t 0.04"
            ])

            if use_legacy_code:
                format_args = []
                codec_args = repre["_profile"].get('codec', [])
                output_args.extend(codec_args)
                # preset's output data
                output_args.extend(repre["_profile"].get('output', []))
            else:
                # Codecs are copied from source for whole input
                format_args, codec_args = self._get_format_codec_args(repre)
                output_args.extend(format_args)
                output_args.extend(codec_args)

            # make sure colors are correct
            output_args.extend([
                "-vf scale=out_color_matrix=bt709",
                "-color_primaries bt709",
                "-color_trc bt709",
                "-colorspace bt709"
            ])

            # scaling none square pixels and 1920 width
            if (
                # Always scale slate if not legacy
                not use_legacy_code or
                # Legacy code required reformat tag
                (use_legacy_code and "reformat" in p_tags)
            ):
                if resolution_ratio_test < delivery_ratio_test:
                    self.log.debug("lower then delivery")
                    width_scale = int(slate_width * scale_factor_by_height)
                    width_half_pad = int((to_width - width_scale) / 2)
                    height_scale = to_height
                    height_half_pad = 0
                else:
                    self.log.debug("heigher then delivery")
                    width_scale = to_width
                    width_half_pad = 0
                    height_scale = int(slate_height * scale_factor_by_width)
                    height_half_pad = int((to_height - height_scale) / 2)

                self.log.debug(
                    "__ width_scale: `{}`".format(width_scale)
                )
                self.log.debug(
                    "__ width_half_pad: `{}`".format(width_half_pad)
                )
                self.log.debug(
                    "__ height_scale: `{}`".format(height_scale)
                )
                self.log.debug(
                    "__ height_half_pad: `{}`".format(height_half_pad)
                )

                scaling_arg = ("scale={0}x{1}:flags=lanczos,"
                               "pad={2}:{3}:{4}:{5}:black,setsar=1").format(
                    width_scale, height_scale, to_width, to_height,
                    width_half_pad, height_half_pad
                )

            vf_back = self.add_video_filter_args(output_args, scaling_arg)
            # add it to output_args
            output_args.insert(0, vf_back)

            # overrides output file
            output_args.append("-y")

            slate_v_path = slate_path.replace(".png", ext)
            output_args.append(
                path_to_subprocess_arg(slate_v_path)
            )
            _remove_at_end.append(slate_v_path)

            slate_args = [
                path_to_subprocess_arg(ffmpeg_path),
                " ".join(input_args),
                " ".join(output_args)
            ]
            slate_subprocess_cmd = " ".join(slate_args)

            # run slate generation subprocess
            self.log.debug(
                "Slate Executing: {}".format(slate_subprocess_cmd)
            )
            openpype.api.run_subprocess(
                slate_subprocess_cmd, shell=True, logger=self.log
            )

            # create ffmpeg concat text file path
            conc_text_file = input_file.replace(ext, "") + "_concat" + ".txt"
            conc_text_path = os.path.join(
                os.path.normpath(stagingdir), conc_text_file)
            _remove_at_end.append(conc_text_path)
            self.log.debug("__ conc_text_path: {}".format(conc_text_path))

            new_line = "\n"
            with open(conc_text_path, "w") as conc_text_f:
                conc_text_f.writelines([
                    "file {}".format(
                        slate_v_path.replace("\\", "/")),
                    new_line,
                    "file {}".format(input_path.replace("\\", "/"))
                ])

            # concat slate and videos together
            concat_args = [
                ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", conc_text_path,
                "-c", "copy",
            ]
            # NOTE: Added because of OP Atom demuxers
            # Add format arguments if there are any
            # - keep format of output
            if format_args:
                concat_args.extend(format_args)
            # Add final output path
            concat_args.append(output_path)

            # ffmpeg concat subprocess
            self.log.debug(
                "Executing concat: {}".format(" ".join(concat_args))
            )
            openpype.api.run_subprocess(
                concat_args, logger=self.log
            )

            self.log.debug("__ repre[tags]: {}".format(repre["tags"]))
            repre_update = {
                "files": output_file,
                "name": repre["name"],
                "tags": [x for x in repre["tags"] if x != "delete"]
            }
            inst_data["representations"][idx].update(repre_update)
            self.log.debug(
                "_ representation {}: `{}`".format(
                    idx, inst_data["representations"][idx]))

            # removing temp files
            for f in _remove_at_end:
                os.remove(f)
                self.log.debug("Removed: `{}`".format(f))

        # Remove any representations tagged for deletion.
        for repre in inst_data.get("representations", []):
            if "delete" in repre.get("tags", []):
                self.log.debug("Removing representation: {}".format(repre))
                inst_data["representations"].remove(repre)

        self.log.debug(inst_data["representations"])

    def _get_slate_path(self, input_file, slates_data):
        slate_path = None
        for sl_n, _slate_path in slates_data.items():
            if "*" in sl_n:
                slate_path = _slate_path
                break
            elif re.search(sl_n, input_file):
                slate_path = _slate_path
                break

        if not slate_path:
            raise AttributeError(
                "Missing slates paths: {}".format(slates_data))

        return slate_path

    def _get_slates_resolution(self, slate_path):
        slate_streams = get_ffprobe_streams(slate_path, self.log)
        # Try to find first stream with defined 'width' and 'height'
        # - this is to avoid order of streams where audio can be as first
        # - there may be a better way (checking `codec_type`?)+
        slate_width = None
        slate_height = None
        for slate_stream in slate_streams:
            if "width" in slate_stream and "height" in slate_stream:
                slate_width = int(slate_stream["width"])
                slate_height = int(slate_stream["height"])
                break

        # Raise exception of any stream didn't define input resolution
        if slate_width is None:
            raise AssertionError((
                "FFprobe couldn't read resolution from input file: \"{}\""
            ).format(slate_path))

        return (slate_width, slate_height)

    def add_video_filter_args(self, args, inserting_arg):
        """
        Fixing video filter argumets to be one long string

        Args:
            args (list): list of string arguments
            inserting_arg (str): string argument we want to add
                                 (without flag `-vf`)

        Returns:
            str: long joined argument to be added back to list of arguments

        """
        # find all video format settings
        vf_settings = [p for p in args
                       for v in ["-filter:v", "-vf"]
                       if v in p]
        self.log.debug("_ vf_settings: `{}`".format(vf_settings))

        # remove them from output args list
        for p in vf_settings:
            self.log.debug("_ remove p: `{}`".format(p))
            args.remove(p)
            self.log.debug("_ args: `{}`".format(args))

        # strip them from all flags
        vf_fixed = [p.replace("-vf ", "").replace("-filter:v ", "")
                    for p in vf_settings]

        self.log.debug("_ vf_fixed: `{}`".format(vf_fixed))
        vf_fixed.insert(0, inserting_arg)
        self.log.debug("_ vf_fixed: `{}`".format(vf_fixed))
        # create new video filter setting
        vf_back = "-vf " + ",".join(vf_fixed)

        return vf_back

    def _get_format_codec_args(self, repre):
        """Detect possible codec arguments from representation."""
        codec_args = []

        # Get one filename of representation files
        filename = repre["files"]
        # If files is list then pick first filename in list
        if isinstance(filename, (tuple, list)):
            filename = filename[0]
        # Get full path to the file
        full_input_path = os.path.join(repre["stagingDir"], filename)

        try:
            # Get information about input file via ffprobe tool
            ffprobe_data = get_ffprobe_data(full_input_path, self.log)
        except Exception:
            self.log.warning(
                "Could not get codec data from input.",
                exc_info=True
            )
            return codec_args

        source_ffmpeg_cmd = repre.get("ffmpeg_cmd")
        format_args = get_ffmpeg_format_args(ffprobe_data, source_ffmpeg_cmd)
        codec_args = get_ffmpeg_codec_args(
            ffprobe_data, source_ffmpeg_cmd, logger=self.log
        )

        return format_args, codec_args
