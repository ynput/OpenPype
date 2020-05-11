import os
from pyblish import api
import pype


class ExtractReviewCutUpVideo(pype.api.Extractor):
    """Cut up clips from long video file"""

    # order = api.ExtractorOrder
    order = api.CollectorOrder + 0.1023
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

        # resolution data
        resolution_width = inst_data["resolutionWidth"]
        resolution_height = inst_data["resolutionHeight"]
        pixel_aspect = inst_data["pixelAspect"]

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

            if not next(
                (t for t in tags
                 if t in ["_cut-bigger", "_cut-smaller"]), None):
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

            input_args.append("-y")

            if start_sec < 0:
                audio_empty = ""
                audio_output = ""
                audio_layer = ""
                v_inp_idx = 0
                black_duration = abs(start_sec)
                start_sec = 0
                duration_sec = float(frame_end - (
                    frame_start + (black_duration * fps)) + 1) / fps

                if audio_check_output:
                    # adding input for empty audio
                    input_args.append("-f lavfi -i anullsrc")
                    audio_empty = (
                        "[0]atrim=duration={black_duration}[ga0];"
                    ).format(**locals())
                    audio_output = ":a=1"
                    audio_layer = "[ga0]"
                    v_inp_idx = 1

                # adding input for video black frame
                input_args.append((
                    "-f lavfi -i \"color=c=black:"
                    "s={resolution_width}x{resolution_height}:r={fps}\""
                ).format(**locals()))

                # concutting black frame togather
                output_args.append((
                    "-filter_complex \""
                    "{audio_empty}"
                    "[{v_inp_idx}]trim=duration={black_duration}[gv0];"
                    "[gv0]{audio_layer}[1:v]"
                    "concat=n=2:v=1{audio_output}\""
                ).format(**locals()))

            input_args.append("-ss {:0.2f}".format(start_sec))
            input_args.append("-t {:0.2f}".format(duration_sec))
            input_args.append("-i {}".format(full_input_path))

            # check if not missing frames at the end
            self.log.debug("media_duration: {}".format(media_duration))
            self.log.debug("frame_end: {}".format(frame_end))

            # make sure it is having no frame to frame comprassion
            output_args.append("-intra")

            # output filename
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
                "stagingDir": staging_dir,
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
            "new representations: {}".format(representations_new))
        instance.data["representations"] = representations_new
