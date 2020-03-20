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

        ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

        # filter out mov and img sequences
        representations_new = representations[:]
        for repre in representations:
            input_args = list()
            output_args = list()

            tags = repre.get("tags", [])

            if "cut-up" not in tags:
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

            full_output_path = os.path.join(
                staging_dir, new_file_name)

            self.log.debug("__ full_input_path: {}".format(full_input_path))
            self.log.debug("__ full_output_path: {}".format(full_output_path))

            input_args.append("-y")
            input_args.append("-i {}".format(full_input_path))

            start_sec = float(frame_start) / fps
            input_args.append("-ss {:0.2f}".format(start_sec))

            output_args.append("-c copy")
            duration_sec = float(frame_end - frame_start + 1) / fps
            output_args.append("-t {:0.2f}".format(duration_sec))

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
                "tags": ["cut-up", "review", "delete"] + self.tags_addition,
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
