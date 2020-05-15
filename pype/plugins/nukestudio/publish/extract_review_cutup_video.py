import os
from pyblish import api
import pype


class ExtractReviewCutUpVideo(pype.api.Extractor):
    """Cut up clips from long video file"""

    order = api.ExtractorOrder
    # order = api.CollectorOrder + 0.1023
    label = "Extract Review CutUp Video"
    hosts = ["nukestudio"]
    families = ["review"]

    # presets
    tags_addition = []

    def process(self, instance):
        inst_data = instance.data
        asset = inst_data['asset']

        # get representation and loop them
        representations = inst_data["representations"]

        # get resolution default
        resolution_width = inst_data["resolutionWidth"]
        resolution_height = inst_data["resolutionHeight"]

        # frame range data
        media_duration = inst_data["mediaDuration"]

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
            for tag in ["_cut-bigger", "_cut-smaller"]:
                if tag in tags:
                    filter_tag = True
                    break
            if not filter_tag:
                continue

            self.log.debug("__ repre: {}".format(repre))

            file = repre.get("files")
            staging_dir = repre.get("stagingDir")
            frame_start = repre.get("frameStart")
            frame_end = repre.get("frameEnd")
            fps = repre.get("fps")
            ext = repre.get("ext")

            new_file_name = "{}_{}".format(asset, file)

            full_input_path = os.path.join(
                staging_dir, file)

            full_output_dir = os.path.join(
                staging_dir, "cuts")

            os.path.isdir(full_output_dir) or os.makedirs(full_output_dir)

            full_output_path = os.path.join(
                full_output_dir, new_file_name)

            self.log.debug("__ full_input_path: {}".format(full_input_path))
            self.log.debug("__ full_output_path: {}".format(full_output_path))

            # check if audio stream is in input video file
            ffprob_cmd = (
                "{ffprobe_path} -i {full_input_path} -show_streams "
                "-select_streams a -loglevel error"
            ).format(**locals())
            self.log.debug("ffprob_cmd: {}".format(ffprob_cmd))
            audio_check_output = pype.api.subprocess(ffprob_cmd)
            self.log.debug("audio_check_output: {}".format(audio_check_output))

            # translate frame to sec
            start_sec = float(frame_start) / fps
            duration_sec = float(frame_end - frame_start + 1) / fps

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
                    resolution_output = pype.api.subprocess((
                        "{ffprobe_path} -i {full_input_path} -v error "
                        "-select_streams v:0 -show_entries "
                        "stream=width,height -of csv=s=x:p=0"
                    ).format(**locals()))

                    x, y = resolution_output.split("x")
                    resolution_width = int(x)
                    resolution_height = int(y)
                except Exception as E:
                    self.log.warning(
                        "Video native resolution is untracable: {}".format(E))

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
                        "[{v_inp_idx}]trim=duration={empty_start_dur}[gv0];"
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
                    empty_end_dur = float(frame_end - media_duration + 1) / fps
                    duration_sec = float(media_duration - frame_start) / fps

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
                    "{video_layer_start}{audio_layer_start}[1:v]{audio_input}"
                    "{video_layer_end}{audio_layer_end}"
                    "concat=n={concat_n}:v=1{audio_output}\""
                ).format(**locals()))

            # append ffmpeg input video clip
            input_args.append("-ss {:0.2f}".format(start_sec))
            input_args.append("-t {:0.2f}".format(duration_sec))
            input_args.append("-i {}".format(full_input_path))

            # add copy audio video codec if only shortening clip
            if ("_cut-bigger" in tags) and (not empty_add):
                output_args.append("-c:v copy")

            # make sure it is having no frame to frame comprassion
            output_args.append("-intra")

            # output filename
            output_args.append("-y")
            output_args.append(full_output_path)

            mov_args = [
                ffmpeg_path,
                " ".join(input_args),
                " ".join(output_args)
            ]
            subprcs_cmd = " ".join(mov_args)

            # run subprocess
            self.log.debug("Executing: {}".format(subprcs_cmd))
            output = pype.api.subprocess(subprcs_cmd)
            self.log.debug("Output: {}".format(output))

            repre_new = {
                "files": new_file_name,
                "stagingDir": full_output_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartFtrack": frame_start,
                "frameEndFtrack": frame_end,
                "step": 1,
                "fps": fps,
                "name": "cut_up_preview",
                "tags": ["review", "delete"] + self.tags_addition,
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
