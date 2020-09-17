import os
import re
import copy
import json
import pyblish.api
import clique
import pype.api
import pype.lib


class ExtractReview(pyblish.api.InstancePlugin):
    """Extracting Review mov file for Ftrack

    Compulsory attribute of representation is tags list with "review",
    otherwise the representation is ignored.

    All new represetnations are created and encoded by ffmpeg following
    presets found in `pype-config/presets/plugins/global/
    publish.json:ExtractReview:outputs`.
    """

    label = "Extract Review"
    order = pyblish.api.ExtractorOrder + 0.02
    families = ["review"]
    hosts = [
        "nuke",
        "maya",
        "shell",
        "nukestudio",
        "premiere",
        "harmony",
        "standalonepublisher"
    ]

    # Supported extensions
    image_exts = ["exr", "jpg", "jpeg", "png", "dpx"]
    video_exts = ["mov", "mp4"]
    supported_exts = image_exts + video_exts

    # FFmpeg tools paths
    ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

    # Preset attributes
    profiles = None

    # Legacy attributes
    outputs = {}
    ext_filter = []
    to_width = 1920
    to_height = 1080

    def process(self, instance):
        # Skip review when requested.
        if not instance.data.get("review", True):
            return

        # ffmpeg doesn't support multipart exrs
        if instance.data.get("multipartExr") is True:
            instance_label = (
                getattr(instance, "label", None)
                or instance.data.get("label")
                or instance.data.get("name")
            )
            self.log.info((
                "Instance \"{}\" contain \"multipartExr\". Skipped."
            ).format(instance_label))
            return

        # Use legacy processing when `profiles` is not set.
        if self.profiles is None:
            return self.legacy_process(instance)

        # Run processing
        self.main_process(instance)

        # Make sure cleanup happens and pop representations with "delete" tag.
        for repre in tuple(instance.data["representations"]):
            tags = repre.get("tags") or []
            if "delete" in tags:
                instance.data["representations"].remove(repre)

    def main_process(self, instance):
        host_name = os.environ["AVALON_APP"]
        task_name = os.environ["AVALON_TASK"]
        family = self.main_family_from_instance(instance)

        self.log.info("Host: \"{}\"".format(host_name))
        self.log.info("Task: \"{}\"".format(task_name))
        self.log.info("Family: \"{}\"".format(family))

        profile = self.find_matching_profile(
            host_name, task_name, family
        )
        if not profile:
            self.log.info((
                "Skipped instance. None of profiles in presets are for"
                " Host: \"{}\" | Family: \"{}\" | Task \"{}\""
            ).format(host_name, family, task_name))
            return

        self.log.debug("Matching profile: \"{}\"".format(json.dumps(profile)))

        instance_families = self.families_from_instance(instance)
        _profile_outputs = self.filter_outputs_by_families(
            profile, instance_families
        )
        if not _profile_outputs:
            self.log.info((
                "Skipped instance. All output definitions from selected"
                " profile does not match to instance families. \"{}\""
            ).format(str(instance_families)))
            return

        # Store `filename_suffix` to save arguments
        profile_outputs = []
        for filename_suffix, definition in _profile_outputs.items():
            definition["filename_suffix"] = filename_suffix
            profile_outputs.append(definition)

        # Loop through representations
        for repre in tuple(instance.data["representations"]):
            tags = repre.get("tags") or []
            if "review" not in tags or "thumbnail" in tags:
                continue

            if "passing" in tags:
                continue

            input_ext = repre["ext"]
            if input_ext.startswith("."):
                input_ext = input_ext[1:]

            if input_ext not in self.supported_exts:
                self.log.info(
                    "Representation has unsupported extension \"{}\"".format(
                        input_ext
                    )
                )
                continue

            # Filter output definition by representation tags (optional)
            outputs = self.filter_outputs_by_tags(profile_outputs, tags)
            if not outputs:
                self.log.info((
                    "Skipped representation. All output definitions from"
                    " selected profile does not match to representation's"
                    " tags. \"{}\""
                ).format(str(tags)))
                continue

            for _output_def in outputs:
                output_def = copy.deepcopy(_output_def)
                # Make sure output definition has "tags" key
                if "tags" not in output_def:
                    output_def["tags"] = []

                # Create copy of representation
                new_repre = copy.deepcopy(repre)

                # Remove "delete" tag from new repre if there is
                if "delete" in new_repre["tags"]:
                    new_repre["tags"].remove("delete")

                # Add additional tags from output definition to representation
                for tag in output_def["tags"]:
                    if tag not in new_repre["tags"]:
                        new_repre["tags"].append(tag)

                self.log.debug(
                    "New representation tags: `{}`".format(new_repre["tags"])
                )

                temp_data = self.prepare_temp_data(instance, repre, output_def)

                ffmpeg_args = self._ffmpeg_arguments(
                    output_def, instance, new_repre, temp_data
                )
                subprcs_cmd = " ".join(ffmpeg_args)

                # run subprocess
                self.log.debug("Executing: {}".format(subprcs_cmd))
                output = pype.api.subprocess(subprcs_cmd, shell=True)
                self.log.debug("Output: {}".format(output))

                output_name = output_def["filename_suffix"]
                if temp_data["without_handles"]:
                    output_name += "_noHandles"

                new_repre.update({
                    "name": output_def["filename_suffix"],
                    "outputName": output_name,
                    "outputDef": output_def,
                    "frameStartFtrack": temp_data["output_frame_start"],
                    "frameEndFtrack": temp_data["output_frame_end"]
                })

                # Force to pop these key if are in new repre
                new_repre.pop("preview", None)
                new_repre.pop("thumbnail", None)
                if "clean_name" in new_repre.get("tags", []):
                    new_repre.pop("outputName")

                # adding representation
                self.log.debug(
                    "Adding new representation: {}".format(new_repre)
                )
                instance.data["representations"].append(new_repre)

    def input_is_sequence(self, repre):
        """Deduce from representation data if input is sequence."""
        # TODO GLOBAL ISSUE - Find better way how to find out if input
        # is sequence. Issues( in theory):
        # - there may be multiple files ant not be sequence
        # - remainders are not checked at all
        # - there can be more than one collection
        return isinstance(repre["files"], (list, tuple))

    def prepare_temp_data(self, instance, repre, output_def):
        """Prepare dictionary with values used across extractor's process.

        All data are collected from instance, context, origin representation
        and output definition.

        There are few required keys in Instance data: "frameStart", "frameEnd"
        and "fps".

        Args:
            instance (Instance): Currently processed instance.
            repre (dict): Representation from which new representation was
                copied.
            output_def (dict): Definition of output of this plugin.

        Returns:
            dict: All data which are used across methods during process.
                Their values should not change during process but new keys
                with values may be added.
        """

        frame_start = instance.data["frameStart"]
        handle_start = instance.data.get(
            "handleStart",
            instance.context.data["handleStart"]
        )
        frame_end = instance.data["frameEnd"]
        handle_end = instance.data.get(
            "handleEnd",
            instance.context.data["handleEnd"]
        )

        frame_start_handle = frame_start - handle_start
        frame_end_handle = frame_end + handle_end

        # Change output frames when output should be without handles
        without_handles = bool("no-handles" in output_def["tags"])
        if without_handles:
            output_frame_start = frame_start
            output_frame_end = frame_end
        else:
            output_frame_start = frame_start_handle
            output_frame_end = frame_end_handle

        return {
            "fps": float(instance.data["fps"]),
            "frame_start": frame_start,
            "frame_end": frame_end,
            "handle_start": handle_start,
            "handle_end": handle_end,
            "frame_start_handle": frame_start_handle,
            "frame_end_handle": frame_end_handle,
            "output_frame_start": int(output_frame_start),
            "output_frame_end": int(output_frame_end),
            "pixel_aspect": instance.data.get("pixelAspect", 1),
            "resolution_width": instance.data.get("resolutionWidth"),
            "resolution_height": instance.data.get("resolutionHeight"),
            "origin_repre": repre,
            "input_is_sequence": self.input_is_sequence(repre),
            "without_handles": without_handles
        }

    def _ffmpeg_arguments(self, output_def, instance, new_repre, temp_data):
        """Prepares ffmpeg arguments for expected extraction.

        Prepares input and output arguments based on output definition and
        input files.

        Args:
            output_def (dict): Currently processed output definition.
            instance (Instance): Currently processed instance.
            new_repre (dict): Reprensetation representing output of this
                process.
            temp_data (dict): Base data for successfull process.
        """

        # Get FFmpeg arguments from profile presets
        out_def_ffmpeg_args = output_def.get("ffmpeg_args") or {}

        ffmpeg_input_args = out_def_ffmpeg_args.get("input") or []
        ffmpeg_output_args = out_def_ffmpeg_args.get("output") or []
        ffmpeg_video_filters = out_def_ffmpeg_args.get("video_filters") or []
        ffmpeg_audio_filters = out_def_ffmpeg_args.get("audio_filters") or []

        # Prepare input and output filepaths
        self.input_output_paths(new_repre, output_def, temp_data)

        # Set output frames len to 1 when ouput is single image
        if (
            temp_data["output_ext_is_image"]
            and not temp_data["output_is_sequence"]
        ):
            output_frames_len = 1

        else:
            output_frames_len = (
                temp_data["output_frame_end"]
                - temp_data["output_frame_start"]
                + 1
            )

        if temp_data["input_is_sequence"]:
            # Set start frame
            ffmpeg_input_args.append(
                "-start_number {}".format(temp_data["output_frame_start"])
            )

            # TODO add fps mapping `{fps: fraction}` ?
            # - e.g.: {
            #     "25": "25/1",
            #     "24": "24/1",
            #     "23.976": "24000/1001"
            # }
            # Add framerate to input when input is sequence
            ffmpeg_input_args.append(
                "-framerate {}".format(temp_data["fps"])
            )

        elif temp_data["without_handles"]:
            start_sec = float(temp_data["handle_start"]) / temp_data["fps"]
            ffmpeg_input_args.append("-ss {:0.2f}".format(start_sec))

            duration_sec = float(output_frames_len / temp_data["fps"])
            ffmpeg_output_args.append("-t {:0.2f}".format(duration_sec))

        # Use shortest input
        ffmpeg_output_args.append("-shortest")

        # Add video/image input path
        ffmpeg_input_args.append(
            "-i \"{}\"".format(temp_data["full_input_path"])
        )

        if temp_data["output_is_sequence"]:
            # Set start frame
            ffmpeg_input_args.append(
                "-start_number {}".format(temp_data["output_frame_start"])
            )

        # Add audio arguments if there are any. Skipped when output are images.
        if not temp_data["output_ext_is_image"]:
            audio_in_args, audio_filters, audio_out_args = self.audio_args(
                instance, temp_data
            )
            ffmpeg_input_args.extend(audio_in_args)
            ffmpeg_audio_filters.extend(audio_filters)
            ffmpeg_output_args.extend(audio_out_args)

        res_filters = self.rescaling_filters(temp_data, output_def, new_repre)
        ffmpeg_video_filters.extend(res_filters)

        ffmpeg_input_args = self.split_ffmpeg_args(ffmpeg_input_args)

        lut_filters = self.lut_filters(new_repre, instance, ffmpeg_input_args)
        ffmpeg_video_filters.extend(lut_filters)

        # Add argument to override output file
        ffmpeg_output_args.append("-y")

        # NOTE This must be latest added item to output arguments.
        ffmpeg_output_args.append(
            "\"{}\"".format(temp_data["full_output_path"])
        )

        return self.ffmpeg_full_args(
            ffmpeg_input_args,
            ffmpeg_video_filters,
            ffmpeg_audio_filters,
            ffmpeg_output_args
        )

    def split_ffmpeg_args(self, in_args):
        """Makes sure all entered arguments are separated in individual items.

        Split each argument string with " -" to identify if string contains
        one or more arguments.
        """
        splitted_args = []
        for arg in in_args:
            sub_args = arg.split(" -")
            if len(sub_args) == 1:
                if arg and arg not in splitted_args:
                    splitted_args.append(arg)
                continue

            for idx, arg in enumerate(sub_args):
                if idx != 0:
                    arg = "-" + arg

                if arg and arg not in splitted_args:
                    splitted_args.append(arg)
        return splitted_args

    def ffmpeg_full_args(
        self, input_args, video_filters, audio_filters, output_args
    ):
        """Post processing of collected FFmpeg arguments.

        Just verify that output arguments does not contain video or audio
        filters which may cause issues because of duplicated argument entry.
        Filters found in output arguments are moved to list they belong to.

        Args:
            input_args (list): All collected ffmpeg arguments with inputs.
            video_filters (list): All collected video filters.
            audio_filters (list): All collected audio filters.
            output_args (list): All collected ffmpeg output arguments with
                output filepath.

        Returns:
            list: Containing all arguments ready to run in subprocess.
        """
        output_args = self.split_ffmpeg_args(output_args)

        video_args_dentifiers = ["-vf", "-filter:v"]
        audio_args_dentifiers = ["-af", "-filter:a"]
        for arg in tuple(output_args):
            for identifier in video_args_dentifiers:
                if identifier in arg:
                    output_args.remove(arg)
                    arg = arg.replace(identifier, "").strip()
                    video_filters.append(arg)

            for identifier in audio_args_dentifiers:
                if identifier in arg:
                    output_args.remove(arg)
                    arg = arg.replace(identifier, "").strip()
                    audio_filters.append(arg)

        all_args = []
        all_args.append(self.ffmpeg_path)
        all_args.extend(input_args)
        if video_filters:
            all_args.append("-filter:v {}".format(",".join(video_filters)))

        if audio_filters:
            all_args.append("-filter:a {}".format(",".join(audio_filters)))

        all_args.extend(output_args)

        return all_args

    def input_output_paths(self, new_repre, output_def, temp_data):
        """Deduce input nad output file paths based on entered data.

        Input may be sequence of images, video file or single image file and
        same can be said about output, this method helps to find out what
        their paths are.

        It is validated that output directory exist and creates if not.

        During process are set "files", "stagingDir", "ext" and
        "sequence_file" (if output is sequence) keys to new representation.
        """

        staging_dir = new_repre["stagingDir"]
        repre = temp_data["origin_repre"]

        if temp_data["input_is_sequence"]:
            collections = clique.assemble(repre["files"])[0]

            full_input_path = os.path.join(
                staging_dir,
                collections[0].format("{head}{padding}{tail}")
            )

            filename = collections[0].format("{head}")
            if filename.endswith("."):
                filename = filename[:-1]

            # Make sure to have full path to one input file
            full_input_path_single_file = os.path.join(
                staging_dir, repre["files"][0]
            )

        else:
            full_input_path = os.path.join(
                staging_dir, repre["files"]
            )
            filename = os.path.splitext(repre["files"])[0]

            # Make sure to have full path to one input file
            full_input_path_single_file = full_input_path

        filename_suffix = output_def["filename_suffix"]

        output_ext = output_def.get("ext")
        # Use input extension if output definition do not specify it
        if output_ext is None:
            output_ext = os.path.splitext(full_input_path)[1]

        # TODO Define if extension should have dot or not
        if output_ext.startswith("."):
            output_ext = output_ext[1:]

        # Store extension to representation
        new_repre["ext"] = output_ext

        self.log.debug("New representation ext: `{}`".format(output_ext))

        # Output is image file sequence witht frames
        output_ext_is_image = bool(output_ext in self.image_exts)
        output_is_sequence = bool(
            output_ext_is_image
            and "sequence" in output_def["tags"]
        )
        if output_is_sequence:
            new_repre_files = []
            frame_start = temp_data["output_frame_start"]
            frame_end = temp_data["output_frame_end"]

            filename_base = "{}_{}".format(filename, filename_suffix)
            # Temporary tempalte for frame filling. Example output:
            # "basename.%04d.exr" when `frame_end` == 1001
            repr_file = "{}.%{:0>2}d.{}".format(
                filename_base, len(str(frame_end)), output_ext
            )

            for frame in range(frame_start, frame_end + 1):
                new_repre_files.append(repr_file % frame)

            new_repre["sequence_file"] = repr_file
            full_output_path = os.path.join(
                staging_dir, filename_base, repr_file
            )

        else:
            repr_file = "{}_{}.{}".format(
                filename, filename_suffix, output_ext
            )
            full_output_path = os.path.join(staging_dir, repr_file)
            new_repre_files = repr_file

        # Store files to representation
        new_repre["files"] = new_repre_files

        # Make sure stagingDire exists
        staging_dir = os.path.normpath(os.path.dirname(full_output_path))
        if not os.path.exists(staging_dir):
            self.log.debug("Creating dir: {}".format(staging_dir))
            os.makedirs(staging_dir)

        # Store stagingDir to representaion
        new_repre["stagingDir"] = staging_dir

        # Store paths to temp data
        temp_data["full_input_path"] = full_input_path
        temp_data["full_input_path_single_file"] = full_input_path_single_file
        temp_data["full_output_path"] = full_output_path

        # Store information about output
        temp_data["output_ext_is_image"] = output_ext_is_image
        temp_data["output_is_sequence"] = output_is_sequence

        self.log.debug("Input path {}".format(full_input_path))
        self.log.debug("Output path {}".format(full_output_path))

    def audio_args(self, instance, temp_data):
        """Prepares FFMpeg arguments for audio inputs."""
        audio_in_args = []
        audio_filters = []
        audio_out_args = []
        audio_inputs = instance.data.get("audio")
        if not audio_inputs:
            return audio_in_args, audio_filters, audio_out_args

        for audio in audio_inputs:
            # NOTE modified, always was expected "frameStartFtrack" which is
            # STRANGE?!!! There should be different key, right?
            # TODO use different frame start!
            offset_seconds = 0
            frame_start_ftrack = instance.data.get("frameStartFtrack")
            if frame_start_ftrack is not None:
                offset_frames = frame_start_ftrack - audio["offset"]
                offset_seconds = offset_frames / temp_data["fps"]

            if offset_seconds > 0:
                audio_in_args.append(
                    "-ss {}".format(offset_seconds)
                )
            elif offset_seconds < 0:
                audio_in_args.append(
                    "-itsoffset {}".format(abs(offset_seconds))
                )

            audio_in_args.append("-i \"{}\"".format(audio["filename"]))

        # NOTE: These were changed from input to output arguments.
        # NOTE: value in "-ac" was hardcoded to 2, changed to audio inputs len.
        # Need to merge audio if there are more than 1 input.
        if len(audio_inputs) > 1:
            audio_out_args.append("-filter_complex amerge")
            audio_out_args.append("-ac {}".format(len(audio_inputs)))

        return audio_in_args, audio_filters, audio_out_args

    def rescaling_filters(self, temp_data, output_def, new_repre):
        """Prepare vieo filters based on tags in new representation.

        It is possible to add letterboxes to output video or rescale to
        different resolution.

        During this preparation "resolutionWidth" and "resolutionHeight" are
        set to new representation.
        """
        filters = []

        letter_box = output_def.get("letter_box")

        # Get instance data
        pixel_aspect = temp_data["pixel_aspect"]

        # NOTE Skipped using instance's resolution
        full_input_path_single_file = temp_data["full_input_path_single_file"]
        input_data = pype.lib.ffprobe_streams(full_input_path_single_file)[0]
        input_width = int(input_data["width"])
        input_height = int(input_data["height"])

        self.log.debug("pixel_aspect: `{}`".format(pixel_aspect))
        self.log.debug("input_width: `{}`".format(input_width))
        self.log.debug("input_height: `{}`".format(input_height))

        # NOTE Setting only one of `width` or `heigth` is not allowed
        output_width = output_def.get("width")
        output_height = output_def.get("height")
        # Use instance resolution if output definition has not set it.
        if output_width is None or output_height is None:
            output_width = temp_data["resolution_width"]
            output_height = temp_data["resolution_height"]

        # Use source's input resolution instance does not have set it.
        if output_width is None or output_height is None:
            self.log.debug("Using resolution from input.")
            output_width = input_width
            output_height = input_height

        output_width = int(output_width)
        output_height = int(output_height)

        self.log.debug(
            "Output resolution is {}x{}".format(output_width, output_height)
        )

        # Skip processing if resolution is same as input's and letterbox is
        # not set
        if (
            output_width == input_width
            and output_height == input_height
            and not letter_box
            and pixel_aspect == 1
        ):
            self.log.debug(
                "Output resolution is same as input's"
                " and \"letter_box\" key is not set. Skipping reformat part."
            )
            new_repre["resolutionWidth"] = input_width
            new_repre["resolutionHeight"] = input_height
            return filters

        # defining image ratios
        input_res_ratio = (
            (float(input_width) * pixel_aspect) / input_height
        )
        output_res_ratio = float(output_width) / float(output_height)
        self.log.debug("input_res_ratio: `{}`".format(input_res_ratio))
        self.log.debug("output_res_ratio: `{}`".format(output_res_ratio))

        # Round ratios to 2 decimal places for comparing
        input_res_ratio = round(input_res_ratio, 2)
        output_res_ratio = round(output_res_ratio, 2)

        # get scale factor
        scale_factor_by_width = (
            float(output_width) / (input_width * pixel_aspect)
        )
        scale_factor_by_height = (
            float(output_height) / input_height
        )

        self.log.debug(
            "scale_factor_by_with: `{}`".format(scale_factor_by_width)
        )
        self.log.debug(
            "scale_factor_by_height: `{}`".format(scale_factor_by_height)
        )

        # letter_box
        if letter_box:
            if input_res_ratio == output_res_ratio:
                letter_box /= pixel_aspect
            elif input_res_ratio < output_res_ratio:
                letter_box /= scale_factor_by_width
            else:
                letter_box /= scale_factor_by_height

            scale_filter = "scale={}x{}:flags=lanczos".format(
                output_width, output_height
            )

            top_box = (
                "drawbox=0:0:iw:round((ih-(iw*(1/{})))/2):t=fill:c=black"
            ).format(letter_box)

            bottom_box = (
                "drawbox=0:ih-round((ih-(iw*(1/{0})))/2)"
                ":iw:round((ih-(iw*(1/{0})))/2):t=fill:c=black"
            ).format(letter_box)

            # Add letter box filters
            filters.extend([scale_filter, "setsar=1", top_box, bottom_box])

        # scaling none square pixels and 1920 width
        if (
            input_height != output_height
            or input_width != output_width
            or pixel_aspect != 1
        ):
            if input_res_ratio < output_res_ratio:
                self.log.debug(
                    "Input's resolution ratio is lower then output's"
                )
                width_scale = int(input_width * scale_factor_by_height)
                width_half_pad = int((output_width - width_scale) / 2)
                height_scale = output_height
                height_half_pad = 0
            else:
                self.log.debug("Input is heigher then output")
                width_scale = output_width
                width_half_pad = 0
                height_scale = int(input_height * scale_factor_by_width)
                height_half_pad = int((output_height - height_scale) / 2)

            self.log.debug("width_scale: `{}`".format(width_scale))
            self.log.debug("width_half_pad: `{}`".format(width_half_pad))
            self.log.debug("height_scale: `{}`".format(height_scale))
            self.log.debug("height_half_pad: `{}`".format(height_half_pad))

            filters.extend([
                "scale={}x{}:flags=lanczos".format(
                    width_scale, height_scale
                ),
                "pad={}:{}:{}:{}:black".format(
                    output_width, output_height,
                    width_half_pad, height_half_pad
                ),
                "setsar=1"
            ])

        new_repre["resolutionWidth"] = output_width
        new_repre["resolutionHeight"] = output_height

        return filters

    def lut_filters(self, new_repre, instance, input_args):
        """Add lut file to output ffmpeg filters."""
        filters = []
        # baking lut file application
        lut_path = instance.data.get("lutPath")
        if not lut_path or "bake-lut" not in new_repre["tags"]:
            return filters

        # Prepare path for ffmpeg argument
        lut_path = lut_path.replace("\\", "/").replace(":", "\\:")

        # Remove gamma from input arguments
        if "-gamma" in input_args:
            input_args.remove("-gamme")

        # Prepare filters
        filters.append("lut3d=file='{}'".format(lut_path))
        # QUESTION hardcoded colormatrix?
        filters.append("colormatrix=bt601:bt709")

        self.log.info("Added Lut to ffmpeg command.")

        return filters

    def main_family_from_instance(self, instance):
        """Returns main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family

    def families_from_instance(self, instance):
        """Returns all families of entered instance."""
        families = []
        family = instance.data.get("family")
        if family:
            families.append(family)

        for family in (instance.data.get("families") or tuple()):
            if family not in families:
                families.append(family)
        return families

    def compile_list_of_regexes(self, in_list):
        """Convert strings in entered list to compiled regex objects."""
        regexes = []
        if not in_list:
            return regexes

        for item in in_list:
            if not item:
                continue

            try:
                regexes.append(re.compile(item))
            except TypeError:
                self.log.warning((
                    "Invalid type \"{}\" value \"{}\"."
                    " Expected string based object. Skipping."
                ).format(str(type(item)), str(item)))

        return regexes

    def validate_value_by_regexes(self, value, in_list):
        """Validates in any regexe from list match entered value.

        Args:
            in_list (list): List with regexes.
            value (str): String where regexes is checked.

        Returns:
            int: Returns `0` when list is not set or is empty. Returns `1` when
                any regex match value and returns `-1` when none of regexes
                match value entered.
        """
        if not in_list:
            return 0

        output = -1
        regexes = self.compile_list_of_regexes(in_list)
        for regex in regexes:
            if re.match(regex, value):
                output = 1
                break
        return output

    def profile_exclusion(self, matching_profiles):
        """Find out most matching profile byt host, task and family match.

        Profiles are selectivelly filtered. Each profile should have
        "__value__" key with list of booleans. Each boolean represents
        existence of filter for specific key (host, taks, family).
        Profiles are looped in sequence. In each sequence are split into
        true_list and false_list. For next sequence loop are used profiles in
        true_list if there are any profiles else false_list is used.

        Filtering ends when only one profile left in true_list. Or when all
        existence booleans loops passed, in that case first profile from left
        profiles is returned.

        Args:
            matching_profiles (list): Profiles with same values.

        Returns:
            dict: Most matching profile.
        """
        self.log.info(
            "Search for first most matching profile in match order:"
            " Host name -> Task name -> Family."
        )
        # Filter all profiles with highest points value. First filter profiles
        # with matching host if there are any then filter profiles by task
        # name if there are any and lastly filter by family. Else use first in
        # list.
        idx = 0
        final_profile = None
        while True:
            profiles_true = []
            profiles_false = []
            for profile in matching_profiles:
                value = profile["__value__"]
                # Just use first profile when idx is greater than values.
                if not idx < len(value):
                    final_profile = profile
                    break

                if value[idx]:
                    profiles_true.append(profile)
                else:
                    profiles_false.append(profile)

            if final_profile is not None:
                break

            if profiles_true:
                matching_profiles = profiles_true
            else:
                matching_profiles = profiles_false

            if len(matching_profiles) == 1:
                final_profile = matching_profiles[0]
                break
            idx += 1

        final_profile.pop("__value__")
        return final_profile

    def find_matching_profile(self, host_name, task_name, family):
        """ Filter profiles by Host name, Task name and main Family.

        Filtering keys are "hosts" (list), "tasks" (list), "families" (list).
        If key is not find or is empty than it's expected to match.

        Args:
            profiles (list): Profiles definition from presets.
            host_name (str): Current running host name.
            task_name (str): Current context task name.
            family (str): Main family of current Instance.

        Returns:
            dict/None: Return most matching profile or None if none of profiles
                match at least one criteria.
        """

        matching_profiles = None
        if not self.profiles:
            return matching_profiles

        highest_profile_points = -1
        # Each profile get 1 point for each matching filter. Profile with most
        # points is returnd. For cases when more than one profile will match
        # are also stored ordered lists of matching values.
        for profile in self.profiles:
            profile_points = 0
            profile_value = []

            # Host filtering
            host_names = profile.get("hosts")
            match = self.validate_value_by_regexes(host_name, host_names)
            if match == -1:
                self.log.debug(
                    "\"{}\" not found in {}".format(host_name, host_names)
                )
                continue
            profile_points += match
            profile_value.append(bool(match))

            # Task filtering
            task_names = profile.get("tasks")
            match = self.validate_value_by_regexes(task_name, task_names)
            if match == -1:
                self.log.debug(
                    "\"{}\" not found in {}".format(task_name, task_names)
                )
                continue
            profile_points += match
            profile_value.append(bool(match))

            # Family filtering
            families = profile.get("families")
            match = self.validate_value_by_regexes(family, families)
            if match == -1:
                self.log.debug(
                    "\"{}\" not found in {}".format(family, families)
                )
                continue
            profile_points += match
            profile_value.append(bool(match))

            if profile_points < highest_profile_points:
                continue

            if profile_points > highest_profile_points:
                matching_profiles = []
                highest_profile_points = profile_points

            if profile_points == highest_profile_points:
                profile["__value__"] = profile_value
                matching_profiles.append(profile)

        if not matching_profiles:
            self.log.warning((
                "None of profiles match your setup."
                " Host \"{}\" | Task: \"{}\" | Family: \"{}\""
            ).format(host_name, task_name, family))
            return

        if len(matching_profiles) == 1:
            # Pop temporary key `__value__`
            matching_profiles[0].pop("__value__")
            return matching_profiles[0]

        self.log.warning((
            "More than one profile match your setup."
            " Host \"{}\" | Task: \"{}\" | Family: \"{}\""
        ).format(host_name, task_name, family))

        return self.profile_exclusion(matching_profiles)

    def families_filter_validation(self, families, output_families_filter):
        """Determines if entered families intersect with families filters.

        All family values are lowered to avoid unexpected results.
        """
        if not output_families_filter:
            return True

        single_families = []
        combination_families = []
        for family_filter in output_families_filter:
            if not family_filter:
                continue
            if isinstance(family_filter, (list, tuple)):
                _family_filter = []
                for family in family_filter:
                    if family:
                        _family_filter.append(family.lower())
                combination_families.append(_family_filter)
            else:
                single_families.append(family_filter.lower())

        for family in single_families:
            if family in families:
                return True

        for family_combination in combination_families:
            valid = True
            for family in family_combination:
                if family not in families:
                    valid = False
                    break

            if valid:
                return True
        return False

    def filter_outputs_by_families(self, profile, families):
        """Return outputs matching input instance families.

        Output definitions without families filter are marked as valid.

        Args:
            profile (dict): Profile from presets matching current context.
            families (list): All families of current instance.

        Returns:
            list: Containg all output definitions matching entered families.
        """
        outputs = profile.get("outputs") or []
        if not outputs:
            return outputs

        # lower values
        # QUESTION is this valid operation?
        families = [family.lower() for family in families]

        filtered_outputs = {}
        for filename_suffix, output_def in outputs.items():
            output_filters = output_def.get("filter")
            # If no filter on output preset, skip filtering and add output
            # profile for farther processing
            if not output_filters:
                filtered_outputs[filename_suffix] = output_def
                continue

            families_filters = output_filters.get("families")
            if not self.families_filter_validation(families, families_filters):
                continue

            filtered_outputs[filename_suffix] = output_def

        return filtered_outputs

    def filter_outputs_by_tags(self, outputs, tags):
        """Filter output definitions by entered representation tags.

        Output definitions without tags filter are marked as valid.

        Args:
            outputs (list): Contain list of output definitions from presets.
            tags (list): Tags of processed representation.

        Returns:
            list: Containg all output definitions matching entered tags.
        """
        filtered_outputs = []
        repre_tags_low = [tag.lower() for tag in tags]
        for output_def in outputs:
            valid = True
            output_filters = output_def.get("filter")
            if output_filters:
                # Check tag filters
                tag_filters = output_filters.get("tags")
                if tag_filters:
                    tag_filters_low = [tag.lower() for tag in tag_filters]
                    valid = False
                    for tag in repre_tags_low:
                        if tag in tag_filters_low:
                            valid = True
                            break

                    if not valid:
                        continue

            if valid:
                filtered_outputs.append(output_def)

        return filtered_outputs

    def legacy_process(self, instance):
        self.log.warning("Legacy review presets are used.")

        output_profiles = self.outputs or {}

        inst_data = instance.data
        context_data = instance.context.data
        fps = float(inst_data.get("fps"))
        frame_start = inst_data.get("frameStart")
        frame_end = inst_data.get("frameEnd")
        handle_start = inst_data.get("handleStart",
                                     context_data.get("handleStart"))
        handle_end = inst_data.get("handleEnd",
                                   context_data.get("handleEnd"))
        pixel_aspect = inst_data.get("pixelAspect", 1)
        resolution_width = inst_data.get("resolutionWidth", self.to_width)
        resolution_height = inst_data.get("resolutionHeight", self.to_height)
        self.log.debug("Families In: `{}`".format(inst_data["families"]))
        self.log.debug("__ frame_start: {}".format(frame_start))
        self.log.debug("__ frame_end: {}".format(frame_end))
        self.log.debug("__ handle_start: {}".format(handle_start))
        self.log.debug("__ handle_end: {}".format(handle_end))

        # get representation and loop them
        representations = inst_data["representations"]

        ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

        # filter out mov and img sequences
        representations_new = representations[:]
        for repre in representations:

            if repre['ext'] not in self.ext_filter:
                continue

            tags = repre.get("tags", [])

            if inst_data.get("multipartExr") is True:
                # ffmpeg doesn't support multipart exrs
                continue

            if "thumbnail" in tags:
                continue

            self.log.info("Try repre: {}".format(repre))

            if "review" not in tags:
                continue

            staging_dir = repre["stagingDir"]

            # iterating preset output profiles
            for name, profile in output_profiles.items():
                repre_new = repre.copy()
                ext = profile.get("ext", None)
                p_tags = profile.get('tags', [])

                # append repre tags into profile tags
                for t in tags:
                    if t not in p_tags:
                        p_tags.append(t)

                self.log.info("p_tags: `{}`".format(p_tags))

                # adding control for presets to be sequence
                # or single file
                is_sequence = ("sequence" in p_tags) and (ext in (
                    "png", "jpg", "jpeg"))

                # no handles switch from profile tags
                no_handles = "no-handles" in p_tags

                self.log.debug("Profile name: {}".format(name))

                if not ext:
                    ext = "mov"
                    self.log.warning(
                        str("`ext` attribute not in output "
                            "profile. Setting to default ext: `mov`"))

                self.log.debug(
                    "instance.families: {}".format(
                        instance.data['families']))
                self.log.debug(
                    "profile.families: {}".format(profile['families']))

                profile_family_check = False
                for _family in profile['families']:
                    if _family in instance.data['families']:
                        profile_family_check = True
                        break

                if not profile_family_check:
                    continue

                if isinstance(repre["files"], list):
                    collections, remainder = clique.assemble(
                        repre["files"])

                    full_input_path = os.path.join(
                        staging_dir, collections[0].format(
                            '{head}{padding}{tail}')
                    )

                    filename = collections[0].format('{head}')
                    if filename.endswith('.'):
                        filename = filename[:-1]
                else:
                    full_input_path = os.path.join(
                        staging_dir, repre["files"])
                    filename = repre["files"].split(".")[0]

                repr_file = filename + "_{0}.{1}".format(name, ext)
                full_output_path = os.path.join(
                    staging_dir, repr_file)

                if is_sequence:
                    filename_base = filename + "_{0}".format(name)
                    repr_file = filename_base + ".%08d.{0}".format(
                        ext)
                    repre_new["sequence_file"] = repr_file
                    full_output_path = os.path.join(
                        staging_dir, filename_base, repr_file)

                self.log.info("input {}".format(full_input_path))
                self.log.info("output {}".format(full_output_path))

                new_tags = [x for x in tags if x != "delete"]

                # add families
                [instance.data["families"].append(t)
                    for t in p_tags
                    if t not in instance.data["families"]]

                # add to
                [new_tags.append(t) for t in p_tags
                 if t not in new_tags]

                self.log.info("new_tags: `{}`".format(new_tags))

                input_args = []
                output_args = []

                # overrides output file
                input_args.append("-y")

                # preset's input data
                input_args.extend(profile.get('input', []))

                # necessary input data
                # adds start arg only if image sequence

                frame_start_handle = frame_start - handle_start
                frame_end_handle = frame_end + handle_end
                if isinstance(repre["files"], list):
                    if frame_start_handle != repre.get(
                            "detectedStart", frame_start_handle):
                        frame_start_handle = repre.get("detectedStart")

                    # exclude handle if no handles defined
                    if no_handles:
                        frame_start_handle = frame_start
                        frame_end_handle = frame_end

                    input_args.append(
                        "-start_number {0} -framerate {1}".format(
                            frame_start_handle, fps))
                else:
                    if no_handles:
                        start_sec = float(handle_start) / fps
                        input_args.append("-ss {:0.2f}".format(start_sec))
                        frame_start_handle = frame_start
                        frame_end_handle = frame_end

                input_args.append("-i {}".format(full_input_path))

                for audio in instance.data.get("audio", []):
                    offset_frames = (
                        instance.data.get("frameStartFtrack") -
                        audio["offset"]
                    )
                    offset_seconds = offset_frames / fps

                    if offset_seconds > 0:
                        input_args.append("-ss")
                    else:
                        input_args.append("-itsoffset")

                        input_args.append(str(abs(offset_seconds)))

                        input_args.extend(
                            ["-i", audio["filename"]]
                        )

                        # Need to merge audio if there are more
                        # than 1 input.
                        if len(instance.data["audio"]) > 1:
                            input_args.extend(
                                [
                                    "-filter_complex",
                                    "amerge",
                                    "-ac",
                                    "2"
                                ]
                            )

                codec_args = profile.get('codec', [])
                output_args.extend(codec_args)
                # preset's output data
                output_args.extend(profile.get('output', []))

                # defining image ratios
                resolution_ratio = (
                    float(resolution_width) * pixel_aspect) / resolution_height
                delivery_ratio = float(self.to_width) / float(self.to_height)
                self.log.debug(
                    "__ resolution_ratio: `{}`".format(resolution_ratio))
                self.log.debug(
                    "__ delivery_ratio: `{}`".format(delivery_ratio))

                # get scale factor
                scale_factor = float(self.to_height) / (
                    resolution_height * pixel_aspect)

                # shorten two decimals long float number for testing conditions
                resolution_ratio_test = float(
                    "{:0.2f}".format(resolution_ratio))
                delivery_ratio_test = float(
                    "{:0.2f}".format(delivery_ratio))

                if resolution_ratio_test != delivery_ratio_test:
                    scale_factor = float(self.to_width) / (
                        resolution_width * pixel_aspect)
                    if int(scale_factor * 100) == 100:
                        scale_factor = (
                            float(self.to_height) / resolution_height
                        )

                self.log.debug("__ scale_factor: `{}`".format(scale_factor))

                # letter_box
                lb = profile.get('letter_box', 0)
                if lb != 0:
                    ffmpeg_width = self.to_width
                    ffmpeg_height = self.to_height
                    if "reformat" not in p_tags:
                        lb /= pixel_aspect
                        if resolution_ratio_test != delivery_ratio_test:
                            ffmpeg_width = resolution_width
                            ffmpeg_height = int(
                                resolution_height * pixel_aspect)
                    else:
                        if resolution_ratio_test != delivery_ratio_test:
                            lb /= scale_factor
                        else:
                            lb /= pixel_aspect

                    output_args.append(str(
                        "-filter:v scale={0}x{1}:flags=lanczos,"
                        "setsar=1,drawbox=0:0:iw:"
                        "round((ih-(iw*(1/{2})))/2):t=fill:"
                        "c=black,drawbox=0:ih-round((ih-(iw*("
                        "1/{2})))/2):iw:round((ih-(iw*(1/{2})))"
                        "/2):t=fill:c=black").format(
                            ffmpeg_width, ffmpeg_height, lb))

                # In case audio is longer than video.
                output_args.append("-shortest")

                if no_handles:
                    duration_sec = float(
                        frame_end_handle - frame_start_handle + 1) / fps

                    output_args.append("-t {:0.2f}".format(duration_sec))

                # output filename
                output_args.append(full_output_path)

                self.log.debug(
                    "__ pixel_aspect: `{}`".format(pixel_aspect))
                self.log.debug(
                    "__ resolution_width: `{}`".format(
                        resolution_width))
                self.log.debug(
                    "__ resolution_height: `{}`".format(
                        resolution_height))

                # scaling none square pixels and 1920 width
                if "reformat" in p_tags:
                    if resolution_ratio_test < delivery_ratio_test:
                        self.log.debug("lower then delivery")
                        width_scale = int(self.to_width * scale_factor)
                        width_half_pad = int((
                            self.to_width - width_scale) / 2)
                        height_scale = self.to_height
                        height_half_pad = 0
                    else:
                        self.log.debug("heigher then delivery")
                        width_scale = self.to_width
                        width_half_pad = 0
                        scale_factor = float(self.to_width) / (float(
                            resolution_width) * pixel_aspect)
                        self.log.debug(
                            "__ scale_factor: `{}`".format(
                                scale_factor))
                        height_scale = int(
                            resolution_height * scale_factor)
                        height_half_pad = int(
                            (self.to_height - height_scale) / 2)

                    self.log.debug(
                        "__ width_scale: `{}`".format(width_scale))
                    self.log.debug(
                        "__ width_half_pad: `{}`".format(
                            width_half_pad))
                    self.log.debug(
                        "__ height_scale: `{}`".format(
                            height_scale))
                    self.log.debug(
                        "__ height_half_pad: `{}`".format(
                            height_half_pad))

                    scaling_arg = str(
                        "scale={0}x{1}:flags=lanczos,"
                        "pad={2}:{3}:{4}:{5}:black,setsar=1"
                    ).format(width_scale, height_scale,
                             self.to_width, self.to_height,
                             width_half_pad,
                             height_half_pad
                             )

                    vf_back = self.add_video_filter_args(
                        output_args, scaling_arg)
                    # add it to output_args
                    output_args.insert(0, vf_back)

                # baking lut file application
                lut_path = instance.data.get("lutPath")
                if lut_path and ("bake-lut" in p_tags):
                    # removing Gama info as it is all baked in lut
                    gamma = next((g for g in input_args
                                  if "-gamma" in g), None)
                    if gamma:
                        input_args.remove(gamma)

                    # create lut argument
                    lut_arg = "lut3d=file='{}'".format(
                        lut_path.replace(
                            "\\", "/").replace(":/", "\\:/")
                    )
                    lut_arg += ",colormatrix=bt601:bt709"

                    vf_back = self.add_video_filter_args(
                        output_args, lut_arg)
                    # add it to output_args
                    output_args.insert(0, vf_back)
                    self.log.info("Added Lut to ffmpeg command")
                    self.log.debug(
                        "_ output_args: `{}`".format(output_args))

                if is_sequence:
                    stg_dir = os.path.dirname(full_output_path)

                    if not os.path.exists(stg_dir):
                        self.log.debug(
                            "creating dir: {}".format(stg_dir))
                        os.mkdir(stg_dir)

                mov_args = [
                    ffmpeg_path,
                    " ".join(input_args),
                    " ".join(output_args)
                ]
                subprcs_cmd = " ".join(mov_args)

                # run subprocess
                self.log.debug("Executing: {}".format(subprcs_cmd))
                output = pype.api.subprocess(subprcs_cmd, shell=True)
                self.log.debug("Output: {}".format(output))

                # create representation data
                repre_new.update({
                    'name': name,
                    'ext': ext,
                    'files': repr_file,
                    "tags": new_tags,
                    "outputName": name,
                    "codec": codec_args,
                    "_profile": profile,
                    "resolutionHeight": resolution_height,
                    "resolutionWidth": resolution_width,
                    "frameStartFtrack": frame_start_handle,
                    "frameEndFtrack": frame_end_handle
                })
                if is_sequence:
                    repre_new.update({
                        "stagingDir": stg_dir,
                        "files": os.listdir(stg_dir)
                    })
                if no_handles:
                    repre_new.update({
                        "outputName": name + "_noHandles",
                        "frameStartFtrack": frame_start,
                        "frameEndFtrack": frame_end
                    })
                if repre_new.get('preview'):
                    repre_new.pop("preview")
                if repre_new.get('thumbnail'):
                    repre_new.pop("thumbnail")

                # adding representation
                self.log.debug("Adding: {}".format(repre_new))
                representations_new.append(repre_new)

        for repre in representations_new:
            if "delete" in repre.get("tags", []):
                representations_new.remove(repre)
            if "clean_name" in repre.get("tags", []):
                repre_new.pop("outputName")

        instance.data.update({
            "reviewToWidth": self.to_width,
            "reviewToHeight": self.to_height
        })

        self.log.debug(
            "new representations: {}".format(representations_new))
        instance.data["representations"] = representations_new

        self.log.debug("Families Out: `{}`".format(instance.data["families"]))

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
