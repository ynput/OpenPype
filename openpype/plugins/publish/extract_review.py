import os
import re
import copy
import json
import shutil

from abc import ABCMeta, abstractmethod
import six

import clique

import pyblish.api
import openpype.api
from openpype.lib import (
    get_ffmpeg_tool_path,
    get_ffprobe_streams,

    path_to_subprocess_arg,

    should_convert_for_ffmpeg,
    convert_for_ffmpeg,
    get_transcode_temp_directory
)
import speedcopy


class ExtractReview(pyblish.api.InstancePlugin):
    """Extracting Review mov file for Ftrack

    Compulsory attribute of representation is tags list with "review",
    otherwise the representation is ignored.

    All new representations are created and encoded by ffmpeg following
    presets found in OpenPype Settings interface at
    `project_settings/global/publish/ExtractReview/profiles:outputs`.
    """

    label = "Extract Review"
    order = pyblish.api.ExtractorOrder + 0.02
    families = ["review"]
    hosts = [
        "nuke",
        "maya",
        "shell",
        "hiero",
        "premiere",
        "harmony",
        "standalonepublisher",
        "fusion",
        "tvpaint",
        "resolve",
        "webpublisher",
        "aftereffects",
        "flame"
    ]

    # Supported extensions
    image_exts = ["exr", "jpg", "jpeg", "png", "dpx"]
    video_exts = ["mov", "mp4"]
    supported_exts = image_exts + video_exts

    alpha_exts = ["exr", "png", "dpx"]

    # FFmpeg tools paths
    ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")

    # Preset attributes
    profiles = None

    def process(self, instance):
        self.log.debug(str(instance.data["representations"]))
        # Skip review when requested.
        if not instance.data.get("review", True):
            return

        # Run processing
        self.main_process(instance)

        # Make sure cleanup happens and pop representations with "delete" tag.
        for repre in tuple(instance.data["representations"]):
            tags = repre.get("tags") or []
            if "delete" in tags and "thumbnail" not in tags:
                instance.data["representations"].remove(repre)

    def _get_outputs_for_instance(self, instance):
        host_name = instance.context.data["hostName"]
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

        subset_name = instance.data.get("subset")
        instance_families = self.families_from_instance(instance)
        filtered_outputs = self.filter_output_defs(
            profile, subset_name, instance_families
        )
        # Store `filename_suffix` to save arguments
        profile_outputs = []
        for filename_suffix, definition in filtered_outputs.items():
            definition["filename_suffix"] = filename_suffix
            profile_outputs.append(definition)

        if not filtered_outputs:
            self.log.info((
                "Skipped instance. All output definitions from selected"
                " profile does not match to instance families. \"{}\""
            ).format(str(instance_families)))
        return profile_outputs

    def _get_outputs_per_representations(self, instance, profile_outputs):
        outputs_per_representations = []
        for repre in instance.data["representations"]:
            repre_name = str(repre.get("name"))
            tags = repre.get("tags") or []
            if "review" not in tags:
                self.log.debug((
                    "Repre: {} - Didn't found \"review\" in tags. Skipping"
                ).format(repre_name))
                continue

            if "thumbnail" in tags:
                self.log.debug((
                    "Repre: {} - Found \"thumbnail\" in tags. Skipping"
                ).format(repre_name))
                continue

            if "passing" in tags:
                self.log.debug((
                    "Repre: {} - Found \"passing\" in tags. Skipping"
                ).format(repre_name))
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
            outputs_per_representations.append((repre, outputs))
        return outputs_per_representations

    @staticmethod
    def get_instance_label(instance):
        return (
            getattr(instance, "label", None)
            or instance.data.get("label")
            or instance.data.get("name")
            or str(instance)
        )

    def main_process(self, instance):
        instance_label = self.get_instance_label(instance)
        self.log.debug("Processing instance \"{}\"".format(instance_label))
        profile_outputs = self._get_outputs_for_instance(instance)
        if not profile_outputs:
            return

        # Loop through representations
        outputs_per_repres = self._get_outputs_per_representations(
            instance, profile_outputs
        )
        fill_data = copy.deepcopy(instance.data["anatomyData"])
        for repre, outputs in outputs_per_repres:
            # Check if input should be preconverted before processing
            # Store original staging dir (it's value may change)
            src_repre_staging_dir = repre["stagingDir"]
            # Receive filepath to first file in representation
            first_input_path = None
            if not self.input_is_sequence(repre):
                first_input_path = os.path.join(
                    src_repre_staging_dir, repre["files"]
                )
            else:
                for filename in repre["files"]:
                    first_input_path = os.path.join(
                        src_repre_staging_dir, filename
                    )
                    break

            # Skip if file is not set
            if first_input_path is None:
                self.log.warning((
                    "Representation \"{}\" have empty files. Skipped."
                ).format(repre["name"]))
                continue

            # Determine if representation requires pre conversion for ffmpeg
            do_convert = should_convert_for_ffmpeg(first_input_path)
            # If result is None the requirement of conversion can't be
            #   determined
            if do_convert is None:
                self.log.info((
                    "Can't determine if representation requires conversion."
                    " Skipped."
                ))
                continue

            # Do conversion if needed
            #   - change staging dir of source representation
            #   - must be set back after output definitions processing
            if do_convert:
                new_staging_dir = get_transcode_temp_directory()
                repre["stagingDir"] = new_staging_dir

                frame_start = instance.data["frameStart"]
                frame_end = instance.data["frameEnd"]
                convert_for_ffmpeg(
                    first_input_path,
                    new_staging_dir,
                    frame_start,
                    frame_end,
                    self.log
                )

            for _output_def in outputs:
                output_def = copy.deepcopy(_output_def)
                # Make sure output definition has "tags" key
                if "tags" not in output_def:
                    output_def["tags"] = []

                if "burnins" not in output_def:
                    output_def["burnins"] = []

                # Create copy of representation
                new_repre = copy.deepcopy(repre)
                # Make sure new representation has origin staging dir
                #   - this is because source representation may change
                #       it's staging dir because of ffmpeg conversion
                new_repre["stagingDir"] = src_repre_staging_dir

                # Remove "delete" tag from new repre if there is
                if "delete" in new_repre["tags"]:
                    new_repre["tags"].remove("delete")

                # Add additional tags from output definition to representation
                for tag in output_def["tags"]:
                    if tag not in new_repre["tags"]:
                        new_repre["tags"].append(tag)

                # Add burnin link from output definition to representation
                for burnin in output_def["burnins"]:
                    if burnin not in new_repre.get("burnins", []):
                        if not new_repre.get("burnins"):
                            new_repre["burnins"] = []
                        new_repre["burnins"].append(str(burnin))

                self.log.debug(
                    "Linked burnins: `{}`".format(new_repre.get("burnins"))
                )

                self.log.debug(
                    "New representation tags: `{}`".format(
                        new_repre.get("tags"))
                )

                temp_data = self.prepare_temp_data(
                    instance, repre, output_def)
                files_to_clean = []
                if temp_data["input_is_sequence"]:
                    self.log.info("Filling gaps in sequence.")
                    files_to_clean = self.fill_sequence_gaps(
                        temp_data["origin_repre"]["files"],
                        new_repre["stagingDir"],
                        temp_data["frame_start"],
                        temp_data["frame_end"])

                # create or update outputName
                output_name = new_repre.get("outputName", "")
                output_ext = new_repre["ext"]
                if output_name:
                    output_name += "_"
                output_name += output_def["filename_suffix"]
                if temp_data["without_handles"]:
                    output_name += "_noHandles"

                # add outputName to anatomy format fill_data
                fill_data.update({
                    "output": output_name,
                    "ext": output_ext
                })

                try:  # temporary until oiiotool is supported cross platform
                    ffmpeg_args = self._ffmpeg_arguments(
                        output_def, instance, new_repre, temp_data, fill_data
                    )
                except ZeroDivisionError:
                    if 'exr' in temp_data["origin_repre"]["ext"]:
                        self.log.debug("Unsupported compression on input " +
                                       "files. Skipping!!!")
                        return
                    raise NotImplementedError

                subprcs_cmd = " ".join(ffmpeg_args)

                # run subprocess
                self.log.debug("Executing: {}".format(subprcs_cmd))

                openpype.api.run_subprocess(
                    subprcs_cmd, shell=True, logger=self.log
                )

                # delete files added to fill gaps
                if files_to_clean:
                    for f in files_to_clean:
                        os.unlink(f)

                new_repre.update({
                    "name": "{}_{}".format(output_name, output_ext),
                    "outputName": output_name,
                    "outputDef": output_def,
                    "frameStartFtrack": temp_data["output_frame_start"],
                    "frameEndFtrack": temp_data["output_frame_end"],
                    "ffmpeg_cmd": subprcs_cmd
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

            # Cleanup temp staging dir after procesisng of output definitions
            if do_convert:
                temp_dir = repre["stagingDir"]
                shutil.rmtree(temp_dir)
                # Set staging dir of source representation back to previous
                #   value
                repre["stagingDir"] = src_repre_staging_dir

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
        frame_end = instance.data["frameEnd"]

        # Try to get handles from instance
        handle_start = instance.data.get("handleStart")
        handle_end = instance.data.get("handleEnd")
        # If even one of handle values is not set on instance use
        # handles from context
        if handle_start is None or handle_end is None:
            handle_start = instance.context.data["handleStart"]
            handle_end = instance.context.data["handleEnd"]

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

        handles_are_set = handle_start > 0 or handle_end > 0

        with_audio = True
        if (
            # Check if has `no-audio` tag
            "no-audio" in output_def["tags"]
            # Check if instance has ny audio in data
            or not instance.data.get("audio")
        ):
            with_audio = False

        input_is_sequence = self.input_is_sequence(repre)
        input_allow_bg = False
        if input_is_sequence and repre["files"]:
            ext = os.path.splitext(repre["files"][0])[1].replace(".", "")
            if ext in self.alpha_exts:
                input_allow_bg = True

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
            "input_is_sequence": input_is_sequence,
            "input_allow_bg": input_allow_bg,
            "with_audio": with_audio,
            "without_handles": without_handles,
            "handles_are_set": handles_are_set
        }

    def _ffmpeg_arguments(
        self, output_def, instance, new_repre, temp_data, fill_data
    ):
        """Prepares ffmpeg arguments for expected extraction.

        Prepares input and output arguments based on output definition and
        input files.

        Args:
            output_def (dict): Currently processed output definition.
            instance (Instance): Currently processed instance.
            new_repre (dict): Representation representing output of this
                process.
            temp_data (dict): Base data for successful process.
        """

        # Get FFmpeg arguments from profile presets
        out_def_ffmpeg_args = output_def.get("ffmpeg_args") or {}

        _ffmpeg_input_args = out_def_ffmpeg_args.get("input") or []
        _ffmpeg_output_args = out_def_ffmpeg_args.get("output") or []
        _ffmpeg_video_filters = out_def_ffmpeg_args.get("video_filters") or []
        _ffmpeg_audio_filters = out_def_ffmpeg_args.get("audio_filters") or []

        # Cleanup empty strings
        ffmpeg_input_args = [
            value for value in _ffmpeg_input_args if value.strip()
        ]
        ffmpeg_video_filters = [
            value for value in _ffmpeg_video_filters if value.strip()
        ]
        ffmpeg_audio_filters = [
            value for value in _ffmpeg_audio_filters if value.strip()
        ]

        ffmpeg_output_args = []
        for value in _ffmpeg_output_args:
            value = value.strip()
            if not value:
                continue
            try:
                value = value.format(**fill_data)
            except Exception:
                self.log.warning(
                    "Failed to format ffmpeg argument: {}".format(value),
                    exc_info=True
                )
                pass
            ffmpeg_output_args.append(value)

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

        duration_seconds = float(output_frames_len / temp_data["fps"])

        if temp_data["input_is_sequence"]:
            # Set start frame of input sequence (just frame in filename)
            # - definition of input filepath
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

        if temp_data["output_is_sequence"]:
            # Set start frame of output sequence (just frame in filename)
            # - this is definition of an output
            ffmpeg_output_args.append(
                "-start_number {}".format(temp_data["output_frame_start"])
            )

        # Change output's duration and start point if should not contain
        # handles
        start_sec = 0
        if temp_data["without_handles"] and temp_data["handles_are_set"]:
            # Set start time without handles
            # - check if handle_start is bigger than 0 to avoid zero division
            if temp_data["handle_start"] > 0:
                start_sec = float(temp_data["handle_start"]) / temp_data["fps"]
                ffmpeg_input_args.append("-ss {:0.10f}".format(start_sec))

            # Set output duration inn seconds
            ffmpeg_output_args.append("-t {:0.10}".format(duration_seconds))

        # Set frame range of output when input or output is sequence
        elif temp_data["output_is_sequence"]:
            ffmpeg_output_args.append("-frames:v {}".format(output_frames_len))

        # Add duration of an input sequence if output is video
        if (
            temp_data["input_is_sequence"]
            and not temp_data["output_is_sequence"]
        ):
            ffmpeg_input_args.append("-to {:0.10f}".format(
                duration_seconds + start_sec
            ))

        # Add video/image input path
        ffmpeg_input_args.append(
            "-i {}".format(
                path_to_subprocess_arg(temp_data["full_input_path"])
            )
        )

        # Add audio arguments if there are any. Skipped when output are images.
        if not temp_data["output_ext_is_image"] and temp_data["with_audio"]:
            audio_in_args, audio_filters, audio_out_args = self.audio_args(
                instance, temp_data, duration_seconds
            )
            ffmpeg_input_args.extend(audio_in_args)
            ffmpeg_audio_filters.extend(audio_filters)
            ffmpeg_output_args.extend(audio_out_args)

        res_filters = self.rescaling_filters(temp_data, output_def, new_repre)
        ffmpeg_video_filters.extend(res_filters)

        ffmpeg_input_args = self.split_ffmpeg_args(ffmpeg_input_args)

        lut_filters = self.lut_filters(new_repre, instance, ffmpeg_input_args)
        ffmpeg_video_filters.extend(lut_filters)

        bg_alpha = 0
        bg_color = output_def.get("bg_color")
        if bg_color:
            bg_red, bg_green, bg_blue, bg_alpha = bg_color

        if bg_alpha > 0:
            if not temp_data["input_allow_bg"]:
                self.log.info((
                    "Output definition has defined BG color input was"
                    " resolved as does not support adding BG."
                ))
            else:
                bg_color_hex = "#{0:0>2X}{1:0>2X}{2:0>2X}".format(
                    bg_red, bg_green, bg_blue
                )
                bg_color_alpha = float(bg_alpha) / 255
                bg_color_str = "{}@{}".format(bg_color_hex, bg_color_alpha)

                self.log.info("Applying BG color {}".format(bg_color_str))
                color_args = [
                    "split=2[bg][fg]",
                    "[bg]drawbox=c={}:replace=1:t=fill[bg]".format(
                        bg_color_str
                    ),
                    "[bg][fg]overlay=format=auto"
                ]
                # Prepend bg color change before all video filters
                # NOTE at the time of creation it is required as video filters
                #   from settings may affect color of BG
                #   e.g. `eq` can remove alpha from input
                for arg in reversed(color_args):
                    ffmpeg_video_filters.insert(0, arg)

        # Add argument to override output file
        ffmpeg_output_args.append("-y")

        # NOTE This must be latest added item to output arguments.
        ffmpeg_output_args.append(
            path_to_subprocess_arg(temp_data["full_output_path"])
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
                if arg.startswith("{} ".format(identifier)):
                    output_args.remove(arg)
                    arg = arg.replace(identifier, "").strip()
                    video_filters.append(arg)

            for identifier in audio_args_dentifiers:
                if arg.startswith("{} ".format(identifier)):
                    output_args.remove(arg)
                    arg = arg.replace(identifier, "").strip()
                    audio_filters.append(arg)

        all_args = []
        all_args.append(path_to_subprocess_arg(self.ffmpeg_path))
        all_args.extend(input_args)
        if video_filters:
            all_args.append("-filter:v")
            all_args.append("\"{}\"".format(",".join(video_filters)))

        if audio_filters:
            all_args.append("-filter:a")
            all_args.append("\"{}\"".format(",".join(audio_filters)))

        all_args.extend(output_args)

        return all_args

    def fill_sequence_gaps(self, files, staging_dir, start_frame, end_frame):
        # type: (list, str, int, int) -> list
        """Fill missing files in sequence by duplicating existing ones.

        This will take nearest frame file and copy it with so as to fill
        gaps in sequence. Last existing file there is is used to for the
        hole ahead.

        Args:
            files (list): List of representation files.
            staging_dir (str): Path to staging directory.
            start_frame (int): Sequence start (no matter what files are there)
            end_frame (int): Sequence end (no matter what files are there)

        Returns:
            list of added files. Those should be cleaned after work
                is done.

        Raises:
            AssertionError: if more then one collection is obtained.

        """
        start_frame = int(start_frame)
        end_frame = int(end_frame)
        collections = clique.assemble(files)[0]
        assert len(collections) == 1, "Multiple collections found."
        col = collections[0]
        # do nothing if sequence is complete
        if list(col.indexes)[0] == start_frame and \
                list(col.indexes)[-1] == end_frame and \
                col.is_contiguous():
            return []

        holes = col.holes()

        # generate ideal sequence
        complete_col = clique.assemble(
            [("{}{:0" + str(col.padding) + "d}{}").format(
                col.head, f, col.tail
            ) for f in range(start_frame, end_frame)]
        )[0][0]  # type: clique.Collection

        new_files = {}
        last_existing_file = None

        for idx in holes.indexes:
            # get previous existing file
            test_file = os.path.normpath(os.path.join(
                staging_dir,
                ("{}{:0" + str(complete_col.padding) + "d}{}").format(
                    complete_col.head, idx - 1, complete_col.tail)))
            if os.path.isfile(test_file):
                new_files[idx] = test_file
                last_existing_file = test_file
            else:
                if not last_existing_file:
                    # previous file is not found (sequence has a hole
                    # at the beginning. Use first available frame
                    # there is.
                    try:
                        last_existing_file = list(col)[0]
                    except IndexError:
                        # empty collection?
                        raise AssertionError(
                            "Invalid sequence collected")
                new_files[idx] = os.path.normpath(
                    os.path.join(staging_dir, last_existing_file))

        files_to_clean = []
        if new_files:
            # so now new files are dict with missing frame as a key and
            # existing file as a value.
            for frame, file in new_files.items():
                self.log.info(
                    "Filling gap {} with {}".format(frame, file))

                hole = os.path.join(
                    staging_dir,
                    ("{}{:0" + str(col.padding) + "d}{}").format(
                        col.head, frame, col.tail))
                speedcopy.copyfile(file, hole)
                files_to_clean.append(hole)

        return files_to_clean

    def input_output_paths(self, new_repre, output_def, temp_data):
        """Deduce input nad output file paths based on entered data.

        Input may be sequence of images, video file or single image file and
        same can be said about output, this method helps to find out what
        their paths are.

        It is validated that output directory exist and creates if not.

        During process are set "files", "stagingDir", "ext" and
        "sequence_file" (if output is sequence) keys to new representation.
        """

        repre = temp_data["origin_repre"]
        src_staging_dir = repre["stagingDir"]
        dst_staging_dir = new_repre["stagingDir"]

        if temp_data["input_is_sequence"]:
            collections = clique.assemble(repre["files"])[0]
            full_input_path = os.path.join(
                src_staging_dir,
                collections[0].format("{head}{padding}{tail}")
            )

            filename = collections[0].format("{head}")
            if filename.endswith("."):
                filename = filename[:-1]

            # Make sure to have full path to one input file
            full_input_path_single_file = os.path.join(
                src_staging_dir, repre["files"][0]
            )

        else:
            full_input_path = os.path.join(
                src_staging_dir, repre["files"]
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
                dst_staging_dir, filename_base, repr_file
            )

        else:
            repr_file = "{}_{}.{}".format(
                filename, filename_suffix, output_ext
            )
            full_output_path = os.path.join(dst_staging_dir, repr_file)
            new_repre_files = repr_file

        # Store files to representation
        new_repre["files"] = new_repre_files

        # Make sure stagingDire exists
        dst_staging_dir = os.path.normpath(os.path.dirname(full_output_path))
        if not os.path.exists(dst_staging_dir):
            self.log.debug("Creating dir: {}".format(dst_staging_dir))
            os.makedirs(dst_staging_dir)

        # Store stagingDir to representaion
        new_repre["stagingDir"] = dst_staging_dir

        # Store paths to temp data
        temp_data["full_input_path"] = full_input_path
        temp_data["full_input_path_single_file"] = full_input_path_single_file
        temp_data["full_output_path"] = full_output_path

        # Store information about output
        temp_data["output_ext_is_image"] = output_ext_is_image
        temp_data["output_is_sequence"] = output_is_sequence

        self.log.debug("Input path {}".format(full_input_path))
        self.log.debug("Output path {}".format(full_output_path))

    def audio_args(self, instance, temp_data, duration_seconds):
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

            # Audio duration is offset from `-ss`
            audio_duration = duration_seconds + offset_seconds

            # Set audio duration
            audio_in_args.append("-to {:0.10f}".format(audio_duration))

            # Add audio input path
            audio_in_args.append("-i {}".format(
                path_to_subprocess_arg(audio["filename"])
            ))

        # NOTE: These were changed from input to output arguments.
        # NOTE: value in "-ac" was hardcoded to 2, changed to audio inputs len.
        # Need to merge audio if there are more than 1 input.
        if len(audio_inputs) > 1:
            audio_out_args.append("-filter_complex amerge")
            audio_out_args.append("-ac {}".format(len(audio_inputs)))

        return audio_in_args, audio_filters, audio_out_args

    def get_letterbox_filters(
        self,
        letter_box_def,
        output_width,
        output_height
    ):
        output = []

        ratio = letter_box_def["ratio"]
        fill_color = letter_box_def["fill_color"]
        f_red, f_green, f_blue, f_alpha = fill_color
        fill_color_hex = "{0:0>2X}{1:0>2X}{2:0>2X}".format(
            f_red, f_green, f_blue
        )
        fill_color_alpha = float(f_alpha) / 255

        line_thickness = letter_box_def["line_thickness"]
        line_color = letter_box_def["line_color"]
        l_red, l_green, l_blue, l_alpha = line_color
        line_color_hex = "{0:0>2X}{1:0>2X}{2:0>2X}".format(
            l_red, l_green, l_blue
        )
        line_color_alpha = float(l_alpha) / 255

        # test ratios and define if pillar or letter boxes
        output_ratio = float(output_width) / float(output_height)
        self.log.debug("Output ratio: {} LetterBox ratio: {}".format(
            output_ratio, ratio
        ))
        pillar = output_ratio > ratio
        need_mask = format(output_ratio, ".3f") != format(ratio, ".3f")
        if not need_mask:
            return []

        if not pillar:
            if fill_color_alpha > 0:
                top_box = (
                    "drawbox=0:0:{width}"
                    ":round(({height}-({width}/{ratio}))/2)"
                    ":t=fill:c={color}@{alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    color=fill_color_hex,
                    alpha=fill_color_alpha
                )

                bottom_box = (
                    "drawbox=0"
                    ":{height}-round(({height}-({width}/{ratio}))/2)"
                    ":{width}"
                    ":round(({height}-({width}/{ratio}))/2)"
                    ":t=fill:c={color}@{alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    color=fill_color_hex,
                    alpha=fill_color_alpha
                )
                output.extend([top_box, bottom_box])

            if line_color_alpha > 0 and line_thickness > 0:
                top_line = (
                    "drawbox=0"
                    ":round(({height}-({width}/{ratio}))/2)-{l_thick}"
                    ":{width}:{l_thick}:t=fill:c={l_color}@{l_alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    l_thick=line_thickness,
                    l_color=line_color_hex,
                    l_alpha=line_color_alpha
                )
                bottom_line = (
                    "drawbox=0"
                    ":{height}-round(({height}-({width}/{ratio}))/2)"
                    ":{width}:{l_thick}:t=fill:c={l_color}@{l_alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    l_thick=line_thickness,
                    l_color=line_color_hex,
                    l_alpha=line_color_alpha
                )
                output.extend([top_line, bottom_line])

        else:
            if fill_color_alpha > 0:
                left_box = (
                    "drawbox=0:0"
                    ":round(({width}-({height}*{ratio}))/2)"
                    ":{height}"
                    ":t=fill:c={color}@{alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    color=fill_color_hex,
                    alpha=fill_color_alpha
                )

                right_box = (
                    "drawbox="
                    "{width}-round(({width}-({height}*{ratio}))/2)"
                    ":0"
                    ":round(({width}-({height}*{ratio}))/2)"
                    ":{height}"
                    ":t=fill:c={color}@{alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    color=fill_color_hex,
                    alpha=fill_color_alpha
                )
                output.extend([left_box, right_box])

            if line_color_alpha > 0 and line_thickness > 0:
                left_line = (
                    "drawbox=round(({width}-({height}*{ratio}))/2)"
                    ":0:{l_thick}:{height}:t=fill:c={l_color}@{l_alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    l_thick=line_thickness,
                    l_color=line_color_hex,
                    l_alpha=line_color_alpha
                )

                right_line = (
                    "drawbox={width}-round(({width}-({height}*{ratio}))/2)"
                    ":0:{l_thick}:{height}:t=fill:c={l_color}@{l_alpha}"
                ).format(
                    width=output_width,
                    height=output_height,
                    ratio=ratio,
                    l_thick=line_thickness,
                    l_color=line_color_hex,
                    l_alpha=line_color_alpha
                )
                output.extend([left_line, right_line])

        return output

    def rescaling_filters(self, temp_data, output_def, new_repre):
        """Prepare vieo filters based on tags in new representation.

        It is possible to add letterboxes to output video or rescale to
        different resolution.

        During this preparation "resolutionWidth" and "resolutionHeight" are
        set to new representation.
        """
        filters = []

        # if reformat input video file is already reforamted from upstream
        reformat_in_baking = bool("reformated" in new_repre["tags"])
        self.log.debug("reformat_in_baking: `{}`".format(reformat_in_baking))

        # Get instance data
        pixel_aspect = temp_data["pixel_aspect"]

        if reformat_in_baking:
            self.log.debug((
                "Using resolution from input. It is already "
                "reformated from upstream process"
            ))
            pixel_aspect = 1

        # NOTE Skipped using instance's resolution
        full_input_path_single_file = temp_data["full_input_path_single_file"]
        try:
            streams = get_ffprobe_streams(
                full_input_path_single_file, self.log
            )
        except Exception as exc:
            raise AssertionError((
                "FFprobe couldn't read information about input file: \"{}\"."
                " Error message: {}"
            ).format(full_input_path_single_file, str(exc)))

        # Try to find first stream with defined 'width' and 'height'
        # - this is to avoid order of streams where audio can be as first
        # - there may be a better way (checking `codec_type`?)
        input_width = None
        input_height = None
        output_width = None
        output_height = None
        for stream in streams:
            if "width" in stream and "height" in stream:
                input_width = int(stream["width"])
                input_height = int(stream["height"])
                break

        # Get instance data
        pixel_aspect = temp_data["pixel_aspect"]

        if reformat_in_baking:
            self.log.debug((
                "Using resolution from input. It is already "
                "reformated from upstream process"
            ))
            pixel_aspect = 1
            output_width = input_width
            output_height = input_height

        # Raise exception of any stream didn't define input resolution
        if input_width is None:
            raise AssertionError((
                "FFprobe couldn't read resolution from input file: \"{}\""
            ).format(full_input_path_single_file))

        # NOTE Setting only one of `width` or `heigth` is not allowed
        # - settings value can't have None but has value of 0
        output_width = output_width or output_def.get("width") or None
        output_height = output_height or output_def.get("height") or None

        # Overscal color
        overscan_color_value = "black"
        overscan_color = output_def.get("overscan_color")
        if overscan_color:
            bg_red, bg_green, bg_blue, _ = overscan_color
            overscan_color_value = "#{0:0>2X}{1:0>2X}{2:0>2X}".format(
                bg_red, bg_green, bg_blue
            )
        self.log.debug("Overscan color: `{}`".format(overscan_color_value))

        # Convert overscan value video filters
        overscan_crop = output_def.get("overscan_crop")
        overscan = OverscanCrop(
            input_width, input_height, overscan_crop, overscan_color_value
        )
        overscan_crop_filters = overscan.video_filters()
        # Add overscan filters to filters if are any and modify input
        #   resolution by it's values
        if overscan_crop_filters:
            filters.extend(overscan_crop_filters)
            input_width = overscan.width()
            input_height = overscan.height()
            # Use output resolution as inputs after cropping to skip usage of
            #   instance data resolution
            if output_width is None or output_height is None:
                output_width = input_width
                output_height = input_height

        # Make sure input width and height is not an odd number
        input_width_is_odd = bool(input_width % 2 != 0)
        input_height_is_odd = bool(input_height % 2 != 0)
        if input_width_is_odd or input_height_is_odd:
            # Add padding to input and make sure this filter is at first place
            filters.append("pad=width=ceil(iw/2)*2:height=ceil(ih/2)*2")

            # Change input width or height as first filter will change them
            if input_width_is_odd:
                self.log.info((
                    "Converting input width from odd to even number. {} -> {}"
                ).format(input_width, input_width + 1))
                input_width += 1

            if input_height_is_odd:
                self.log.info((
                    "Converting input height from odd to even number. {} -> {}"
                ).format(input_height, input_height + 1))
                input_height += 1

        self.log.debug("pixel_aspect: `{}`".format(pixel_aspect))
        self.log.debug("input_width: `{}`".format(input_width))
        self.log.debug("input_height: `{}`".format(input_height))

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

        # Make sure output width and height is not an odd number
        # When this can happen:
        # - if output definition has set width and height with odd number
        # - `instance.data` contain width and height with odd numbeer
        if output_width % 2 != 0:
            self.log.warning((
                "Converting output width from odd to even number. {} -> {}"
            ).format(output_width, output_width + 1))
            output_width += 1

        if output_height % 2 != 0:
            self.log.warning((
                "Converting output height from odd to even number. {} -> {}"
            ).format(output_height, output_height + 1))
            output_height += 1

        self.log.debug(
            "Output resolution is {}x{}".format(output_width, output_height)
        )

        letter_box_def = output_def["letter_box"]
        letter_box_enabled = letter_box_def["enabled"]

        # Skip processing if resolution is same as input's and letterbox is
        # not set
        if (
            output_width == input_width
            and output_height == input_height
            and not letter_box_enabled
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
                "pad={}:{}:{}:{}:{}".format(
                    output_width, output_height,
                    width_half_pad, height_half_pad,
                    overscan_color_value
                ),
                "setsar=1"
            ])

        # letter_box
        if letter_box_enabled:
            filters.extend(
                self.get_letterbox_filters(
                    letter_box_def,
                    output_width,
                    output_height
                )
            )

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
        """Validates in any regex from list match entered value.

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

        Profiles are selectively filtered. Each profile should have
        "__value__" key with list of booleans. Each boolean represents
        existence of filter for specific key (host, tasks, family).
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
        # points is returned. For cases when more than one profile will match
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

    def filter_output_defs(self, profile, subset_name, families):
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

            # Subsets name filters
            subset_filters = [
                subset_filter
                for subset_filter in output_filters.get("subsets", [])
                # Skip empty strings
                if subset_filter
            ]
            if subset_name and subset_filters:
                match = False
                for subset_filter in subset_filters:
                    compiled = re.compile(subset_filter)
                    if compiled.search(subset_name):
                        match = True
                        break

                if not match:
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

    def add_video_filter_args(self, args, inserting_arg):
        """
        Fixing video filter arguments to be one long string

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


@six.add_metaclass(ABCMeta)
class _OverscanValue:
    def __repr__(self):
        return "<{}> {}".format(self.__class__.__name__, str(self))

    @abstractmethod
    def copy(self):
        """Create a copy of object."""
        pass

    @abstractmethod
    def size_for(self, value):
        """Calculate new value for passed value."""
        pass


class PixValueExplicit(_OverscanValue):
    def __init__(self, value):
        self._value = int(value)

    def __str__(self):
        return "{}px".format(self._value)

    def copy(self):
        return PixValueExplicit(self._value)

    def size_for(self, value):
        if self._value == 0:
            return value
        return self._value


class PercentValueExplicit(_OverscanValue):
    def __init__(self, value):
        self._value = float(value)

    def __str__(self):
        return "{}%".format(abs(self._value))

    def copy(self):
        return PercentValueExplicit(self._value)

    def size_for(self, value):
        if self._value == 0:
            return value
        return int((value / 100) * self._value)


class PixValueRelative(_OverscanValue):
    def __init__(self, value):
        self._value = int(value)

    def __str__(self):
        sign = "-" if self._value < 0 else "+"
        return "{}{}px".format(sign, abs(self._value))

    def copy(self):
        return PixValueRelative(self._value)

    def size_for(self, value):
        return value + self._value


class PercentValueRelative(_OverscanValue):
    def __init__(self, value):
        self._value = float(value)

    def __str__(self):
        return "{}%".format(self._value)

    def copy(self):
        return PercentValueRelative(self._value)

    def size_for(self, value):
        if self._value == 0:
            return value

        offset = int((value / 100) * self._value)

        return value + offset


class PercentValueRelativeSource(_OverscanValue):
    def __init__(self, value, source_sign):
        self._value = float(value)
        if source_sign not in ("-", "+"):
            raise ValueError(
                "Invalid sign value \"{}\" expected \"-\" or \"+\"".format(
                    source_sign
                )
            )
        self._source_sign = source_sign

    def __str__(self):
        return "{}%{}".format(self._value, self._source_sign)

    def copy(self):
        return PercentValueRelativeSource(self._value, self._source_sign)

    def size_for(self, value):
        if self._value == 0:
            return value
        return int((value * 100) / (100 - self._value))


class OverscanCrop:
    """Helper class to read overscan string and calculate output resolution.

    It is possible to enter single value for both width and heigh or two values
    for width and height. Overscan string may have a few variants. Each variant
    define output size for input size.

    ### Example
    For input size: 2200px

    | String   | Output | Description                                     |
    |----------|--------|-------------------------------------------------|
    | ""       | 2200px | Empty string does nothing.                      |
    | "10%"    | 220px  | Explicit percent size.                          |
    | "-10%"   | 1980px | Relative percent size (decrease).               |
    | "+10%"   | 2420px | Relative percent size (increase).               |
    | "-10%+"  | 2000px | Relative percent size to output size.           |
    | "300px"  | 300px  | Explicit output size cropped or expanded.       |
    | "-300px" | 1900px | Relative pixel size (decrease).                 |
    | "+300px" | 2500px | Relative pixel size (increase).                 |
    | "300"    | 300px  | Value without "%" and "px" is used as has "px". |

    Value without sign (+/-) in is always explicit and value with sign is
    relative. Output size for "200px" and "+200px" are not the same.
    Values "0", "0px" or "0%" are ignored.

    All values that cause output resolution smaller than 1 pixel are invalid.

    Value "-10%+" is a special case which says that input's resolution is
    bigger by 10% than expected output.

    It is possible to combine these variants to define different output for
    width and height.

    Resolution: 2000px 1000px

    | String        | Output        |
    |---------------|---------------|
    | "100px 120px" | 2100px 1120px |
    | "-10% -200px" | 1800px 800px  |
    """

    item_regex = re.compile(r"([\+\-])?([0-9]+)(.+)?")
    relative_source_regex = re.compile(r"%([\+\-])")

    def __init__(
        self, input_width, input_height, string_value, overscal_color=None
    ):
        # Make sure that is not None
        string_value = string_value or ""

        self.input_width = input_width
        self.input_height = input_height
        self.overscal_color = overscal_color

        width, height = self._convert_string_to_values(string_value)
        self._width_value = width
        self._height_value = height

        self._string_value = string_value

    def __str__(self):
        return "{}".format(self._string_value)

    def __repr__(self):
        return "<{}>".format(self.__class__.__name__)

    def width(self):
        """Calculated width."""
        return self._width_value.size_for(self.input_width)

    def height(self):
        """Calculated height."""
        return self._height_value.size_for(self.input_height)

    def video_filters(self):
        """FFmpeg video filters to achieve expected result.

        Filter may be empty, use "crop" filter, "pad" filter or combination of
        "crop" and "pad".

        Returns:
            list: FFmpeg video filters.
        """
        # crop=width:height:x:y - explicit start x, y position
        # crop=width:height     - x, y are related to center by width/height
        # pad=width:heigth:x:y  - explicit start x, y position
        # pad=width:heigth      - x, y are set to 0 by default

        width = self.width()
        height = self.height()

        output = []
        if self.input_width == width and self.input_height == height:
            return output

        # Make sure resolution has odd numbers
        if width % 2 == 1:
            width -= 1

        if height % 2 == 1:
            height -= 1

        if width <= self.input_width and height <= self.input_height:
            output.append("crop={}:{}".format(width, height))

        elif width >= self.input_width and height >= self.input_height:
            output.append(
                "pad={}:{}:(iw-ow)/2:(ih-oh)/2:{}".format(
                    width, height, self.overscal_color
                )
            )

        elif width > self.input_width and height < self.input_height:
            output.append("crop=iw:{}".format(height))
            output.append("pad={}:ih:(iw-ow)/2:(ih-oh)/2:{}".format(
                width, self.overscal_color
            ))

        elif width < self.input_width and height > self.input_height:
            output.append("crop={}:ih".format(width))
            output.append("pad=iw:{}:(iw-ow)/2:(ih-oh)/2:{}".format(
                height, self.overscal_color
            ))

        return output

    def _convert_string_to_values(self, orig_string_value):
        string_value = orig_string_value.strip().lower()
        if not string_value:
            return [PixValueRelative(0), PixValueRelative(0)]

        # Replace "px" (and spaces before) with single space
        string_value = re.sub(r"([ ]+)?px", " ", string_value)
        string_value = re.sub(r"([ ]+)%", "%", string_value)
        # Make sure +/- sign at the beggining of string is next to number
        string_value = re.sub(r"^([\+\-])[ ]+", "\g<1>", string_value)
        # Make sure +/- sign in the middle has zero spaces before number under
        #   which belongs
        string_value = re.sub(
            r"[ ]([\+\-])[ ]+([0-9])",
            r" \g<1>\g<2>",
            string_value
        )
        string_parts = [
            part
            for part in string_value.split(" ")
            if part
        ]

        error_msg = "Invalid string for rescaling \"{}\"".format(
            orig_string_value
        )
        if 1 > len(string_parts) > 2:
            raise ValueError(error_msg)

        output = []
        for item in string_parts:
            groups = self.item_regex.findall(item)
            if not groups:
                raise ValueError(error_msg)

            relative_sign, value, ending = groups[0]
            if not relative_sign:
                if not ending:
                    output.append(PixValueExplicit(value))
                else:
                    output.append(PercentValueExplicit(value))
            else:
                source_sign_group = self.relative_source_regex.findall(ending)
                if not ending:
                    output.append(PixValueRelative(int(relative_sign + value)))

                elif source_sign_group:
                    source_sign = source_sign_group[0]
                    output.append(PercentValueRelativeSource(
                        float(relative_sign + value), source_sign
                    ))
                else:
                    output.append(
                        PercentValueRelative(float(relative_sign + value))
                    )

        if len(output) == 1:
            width = output.pop(0)
            height = width.copy()
        else:
            width, height = output

        return width, height
