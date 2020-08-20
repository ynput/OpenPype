import os
import pype.api
import pype.lib
import pyblish


class ExtractReviewSlate(pype.api.Extractor):
    """
    Will add slate frame at the start of the video files
    """

    label = "Review with Slate frame"
    order = pyblish.api.ExtractorOrder + 0.031
    families = ["slate", "review"]
    match = pyblish.api.Subset

    hosts = ["nuke", "maya", "shell"]
    optional = True

    def process(self, instance):
        inst_data = instance.data
        if "representations" not in inst_data:
            raise RuntimeError("Burnin needs already created mov to work on.")

        suffix = "_slate"
        slate_path = inst_data.get("slateFrame")
        ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

        slate_stream = pype.lib.ffprobe_streams(slate_path)[0]
        slate_width = slate_stream["width"]
        slate_height = slate_stream["height"]

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

            # values are set in ExtractReview
            if use_legacy_code:
                to_width = inst_data["reviewToWidth"]
                to_height = inst_data["reviewToHeight"]
            else:
                to_width = repre["resolutionWidth"]
                to_height = repre["resolutionHeight"]

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

            stagingdir = repre["stagingDir"]
            input_file = "{0}".format(repre["files"])

            ext = os.path.splitext(input_file)[1]
            output_file = input_file.replace(ext, "") + suffix + ext

            input_path = os.path.join(
                os.path.normpath(stagingdir), repre["files"])
            self.log.debug("__ input_path: {}".format(input_path))
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
            input_args.append("-loop 1 -i {}".format(slate_path))
            input_args.extend([
                "-r {}".format(fps),
                "-t 0.04"]
            )

            if use_legacy_code:
                codec_args = repre["_profile"].get('codec', [])
                output_args.extend(codec_args)
                # preset's output data
                output_args.extend(repre["_profile"].get('output', []))
            else:
                # Codecs are copied from source for whole input
                codec_args = self.codec_args(repre)
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
            output_args.append(slate_v_path)
            _remove_at_end.append(slate_v_path)

            slate_args = [
                ffmpeg_path,
                " ".join(input_args),
                " ".join(output_args)
            ]
            slate_subprcs_cmd = " ".join(slate_args)

            # run slate generation subprocess
            self.log.debug("Slate Executing: {}".format(slate_subprcs_cmd))
            slate_output = pype.api.subprocess(slate_subprcs_cmd, shell=True)
            self.log.debug("Slate Output: {}".format(slate_output))

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
            conc_input_args = ["-y", "-f concat", "-safe 0"]
            conc_input_args.append("-i {}".format(conc_text_path))

            conc_output_args = ["-c copy"]
            conc_output_args.append(output_path)

            concat_args = [
                ffmpeg_path,
                " ".join(conc_input_args),
                " ".join(conc_output_args)
            ]
            concat_subprcs_cmd = " ".join(concat_args)

            # ffmpeg concat subprocess
            self.log.debug("Executing concat: {}".format(concat_subprcs_cmd))
            concat_output = pype.api.subprocess(concat_subprcs_cmd, shell=True)
            self.log.debug("Output concat: {}".format(concat_output))

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

    def codec_args(self, repre):
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
            streams = pype.lib.ffprobe_streams(full_input_path)
        except Exception:
            self.log.warning(
                "Could not get codec data from input.",
                exc_info=True
            )
            return codec_args

        codec_name = streams[0].get("codec_name")
        if codec_name:
            codec_args.append("-codec:v {}".format(codec_name))

        profile_name = streams[0].get("profile")
        if profile_name:
            profile_name = profile_name.replace(" ", "_").lower()
            codec_args.append("-profile:v {}".format(profile_name))

        pix_fmt = streams[0].get("pix_fmt")
        if pix_fmt:
            codec_args.append("-pix_fmt {}".format(pix_fmt))
        return codec_args
