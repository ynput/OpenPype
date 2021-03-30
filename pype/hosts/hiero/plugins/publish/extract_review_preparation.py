import os
import sys
import six
import errno
from pyblish import api
import pype
import clique
from avalon.vendor import filelink


class ExtractReviewPreparation(pype.api.Extractor):
    """Cut up clips from long video file"""

    order = api.ExtractorOrder
    label = "Extract Review Preparation"
    hosts = ["hiero"]
    families = ["review"]

    # presets
    tags_addition = []

    def process(self, instance):
        inst_data = instance.data
        asset = inst_data["asset"]
        review_item_data = instance.data.get("reviewItemData")

        # get representation and loop them
        representations = inst_data["representations"]

        # get resolution default
        resolution_width = inst_data["resolutionWidth"]
        resolution_height = inst_data["resolutionHeight"]

        # frame range data
        media_duration = review_item_data["mediaDuration"]

        ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")
        ffprobe_path = pype.lib.get_ffmpeg_tool_path("ffprobe")

        # filter out mov and img sequences
        representations_new = representations[:]
        for repre in representations:
            input_args = list()
            output_args = list()

            tags = repre.get("tags", [])

            # check if supported tags are in representation for activation
            filter_tag = False
            for tag in ["_cut-bigger", "prep"]:
                if tag in tags:
                    filter_tag = True
                    break
            if not filter_tag:
                continue

            self.log.debug("__ repre: {}".format(repre))

            files = repre.get("files")
            staging_dir = repre.get("stagingDir")
            fps = repre.get("fps")
            ext = repre.get("ext")

            # make paths
            full_output_dir = os.path.join(
                staging_dir, "cuts")

            if isinstance(files, list):
                new_files = list()

                # frame range delivery included handles
                frame_start = (
                    inst_data["frameStart"] - inst_data["handleStart"])
                frame_end = (
                    inst_data["frameEnd"] + inst_data["handleEnd"])
                self.log.debug("_ frame_start: {}".format(frame_start))
                self.log.debug("_ frame_end: {}".format(frame_end))

                # make collection from input files list
                collections, remainder = clique.assemble(files)
                collection = collections.pop()
                self.log.debug("_ collection: {}".format(collection))

                # name components
                head = collection.format("{head}")
                padding = collection.format("{padding}")
                tail = collection.format("{tail}")
                self.log.debug("_ head: {}".format(head))
                self.log.debug("_ padding: {}".format(padding))
                self.log.debug("_ tail: {}".format(tail))

                # make destination file with instance data
                # frame start and end range
                index = 0
                for image in collection:
                    dst_file_num = frame_start + index
                    dst_file_name = head + str(padding % dst_file_num) + tail
                    src = os.path.join(staging_dir, image)
                    dst = os.path.join(full_output_dir, dst_file_name)
                    self.log.info("Creating temp hardlinks: {}".format(dst))
                    self.hardlink_file(src, dst)
                    new_files.append(dst_file_name)
                    index += 1

                self.log.debug("_ new_files: {}".format(new_files))

            else:
                # ffmpeg when single file
                new_files = "{}_{}".format(asset, files)

                # frame range
                frame_start = repre.get("frameStart")
                frame_end = repre.get("frameEnd")

                full_input_path = os.path.join(
                    staging_dir, files)

                os.path.isdir(full_output_dir) or os.makedirs(full_output_dir)

                full_output_path = os.path.join(
                    full_output_dir, new_files)

                self.log.debug(
                    "__ full_input_path: {}".format(full_input_path))
                self.log.debug(
                    "__ full_output_path: {}".format(full_output_path))

                # check if audio stream is in input video file
                ffprob_cmd = (
                    "\"{ffprobe_path}\" -i \"{full_input_path}\" -show_streams"
                    " -select_streams a -loglevel error"
                ).format(**locals())

                self.log.debug("ffprob_cmd: {}".format(ffprob_cmd))
                audio_check_output = pype.api.run_subprocess(ffprob_cmd)
                self.log.debug(
                    "audio_check_output: {}".format(audio_check_output))

                # Fix one frame difference
                """ TODO: this is just work-around for issue:
                          https://github.com/pypeclub/pype/issues/659
                """
                frame_duration_extend = 1
                if audio_check_output and ("audio" in inst_data["families"]):
                    frame_duration_extend = 0

                # translate frame to sec
                start_sec = float(frame_start) / fps
                duration_sec = float(
                    (frame_end - frame_start) + frame_duration_extend) / fps

                empty_add = None

                # check if not missing frames at start
                if (start_sec < 0) or (media_duration < frame_end):
                    # for later swithing off `-c:v copy` output arg
                    empty_add = True

                    # init empty variables
                    video_empty_start = video_layer_start = ""
                    audio_empty_start = audio_layer_start = ""
                    video_empty_end = video_layer_end = ""
                    audio_empty_end = audio_layer_end = ""
                    audio_input = audio_output = ""
                    v_inp_idx = 0
                    concat_n = 1

                    # try to get video native resolution data
                    try:
                        resolution_output = pype.api.run_subprocess((
                            "\"{ffprobe_path}\" -i \"{full_input_path}\""
                            " -v error "
                            "-select_streams v:0 -show_entries "
                            "stream=width,height -of csv=s=x:p=0"
                        ).format(**locals()))

                        x, y = resolution_output.split("x")
                        resolution_width = int(x)
                        resolution_height = int(y)
                    except Exception as _ex:
                        self.log.warning(
                            "Video native resolution is untracable: {}".format(
                                _ex))

                    if audio_check_output:
                        # adding input for empty audio
                        input_args.append("-f lavfi -i anullsrc")

                        # define audio empty concat variables
                        audio_input = "[1:a]"
                        audio_output = ":a=1"
                        v_inp_idx = 1

                    # adding input for video black frame
                    input_args.append((
                        "-f lavfi -i \"color=c=black:"
                        "s={resolution_width}x{resolution_height}:r={fps}\""
                    ).format(**locals()))

                    if (start_sec < 0):
                        # recalculate input video timing
                        empty_start_dur = abs(start_sec)
                        start_sec = 0
                        duration_sec = float(frame_end - (
                            frame_start + (empty_start_dur * fps)) + 1) / fps

                        # define starting empty video concat variables
                        video_empty_start = (
                            "[{v_inp_idx}]trim=duration={empty_start_dur}[gv0];"  # noqa
                        ).format(**locals())
                        video_layer_start = "[gv0]"

                        if audio_check_output:
                            # define starting empty audio concat variables
                            audio_empty_start = (
                                "[0]atrim=duration={empty_start_dur}[ga0];"
                            ).format(**locals())
                            audio_layer_start = "[ga0]"

                        # alter concat number of clips
                        concat_n += 1

                    # check if not missing frames at the end
                    if (media_duration < frame_end):
                        # recalculate timing
                        empty_end_dur = float(
                            frame_end - media_duration + 1) / fps
                        duration_sec = float(
                            media_duration - frame_start) / fps

                        # define ending empty video concat variables
                        video_empty_end = (
                            "[{v_inp_idx}]trim=duration={empty_end_dur}[gv1];"
                        ).format(**locals())
                        video_layer_end = "[gv1]"

                        if audio_check_output:
                            # define ending empty audio concat variables
                            audio_empty_end = (
                                "[0]atrim=duration={empty_end_dur}[ga1];"
                            ).format(**locals())
                            audio_layer_end = "[ga0]"

                        # alter concat number of clips
                        concat_n += 1

                    # concatting black frame togather
                    output_args.append((
                        "-filter_complex \""
                        "{audio_empty_start}"
                        "{video_empty_start}"
                        "{audio_empty_end}"
                        "{video_empty_end}"
                        "{video_layer_start}{audio_layer_start}[1:v]{audio_input}"  # noqa
                        "{video_layer_end}{audio_layer_end}"
                        "concat=n={concat_n}:v=1{audio_output}\""
                    ).format(**locals()))

                # append ffmpeg input video clip
                input_args.append("-ss {}".format(start_sec))
                input_args.append("-t {}".format(duration_sec))
                input_args.append("-i \"{}\"".format(full_input_path))

                # add copy audio video codec if only shortening clip
                if ("_cut-bigger" in tags) and (not empty_add):
                    output_args.append("-c:v copy")

                # make sure it is having no frame to frame comprassion
                output_args.append("-intra")

                # output filename
                output_args.append("-y \"{}\"".format(full_output_path))

                mov_args = [
                    "\"{}\"".format(ffmpeg_path),
                    " ".join(input_args),
                    " ".join(output_args)
                ]
                subprcs_cmd = " ".join(mov_args)

                # run subprocess
                self.log.debug("Executing: {}".format(subprcs_cmd))
                output = pype.api.run_subprocess(subprcs_cmd)
                self.log.debug("Output: {}".format(output))

            repre_new = {
                "files": new_files,
                "stagingDir": full_output_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartFtrack": frame_start,
                "frameEndFtrack": frame_end,
                "step": 1,
                "fps": fps,
                "name": "cut_up_preview",
                "tags": [
                    "review", "ftrackreview", "delete"] + self.tags_addition,
                "ext": ext,
                "anatomy_template": "publish"
            }

            representations_new.append(repre_new)

        for repre in representations_new:
            if ("delete" in repre.get("tags", [])) and (
                    "cut_up_preview" not in repre["name"]):
                representations_new.remove(repre)

        self.log.debug(
            "Representations: {}".format(representations_new))
        instance.data["representations"] = representations_new

    def hardlink_file(self, src, dst):
        dirname = os.path.dirname(dst)

        # make sure the destination folder exist
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                six.reraise(*sys.exc_info())

        # create hardlined file
        try:
            filelink.create(src, dst, filelink.HARDLINK)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                six.reraise(*sys.exc_info())
