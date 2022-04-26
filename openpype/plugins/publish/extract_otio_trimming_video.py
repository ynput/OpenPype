"""
Requires:
    instance -> otioTrimmingRange
    instance -> representations

"""

import os
from pyblish import api
import openpype
from copy import deepcopy


class ExtractOTIOTrimmingVideo(openpype.api.Extractor):
    """
    Trimming video file longer then required lenght

    """
    order = api.ExtractorOrder
    label = "Extract OTIO trim longer video"
    families = ["trim"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, instance):
        self.staging_dir = self.staging_dir(instance)
        otio_trim_range = instance.data["otioTrimmingRange"]
        representations = instance.data["representations"]
        self.log.debug("otio_trim_range: {}".format(otio_trim_range))
        self.log.debug("self.staging_dir: {}".format(self.staging_dir))

        # get corresponding representation
        for _repre in representations:
            if "trim" not in _repre.get("tags", []):
                continue

            input_file = _repre["files"]
            input_file_path = os.path.normpath(os.path.join(
                _repre["stagingDir"], input_file
            ))
            self.log.debug("input_file_path: {}".format(input_file_path))

            # trim via ffmpeg
            new_file = self._ffmpeg_trim_seqment(
                input_file_path, otio_trim_range)

            # prepare new representation data
            repre_data = deepcopy(_repre)
            # remove tags as we dont need them
            repre_data.pop("tags")
            repre_data["stagingDir"] = self.staging_dir
            repre_data["files"] = new_file

            # romove `trim` tagged representation
            representations.remove(_repre)
            representations.append(repre_data)
            self.log.debug(repre_data)

        self.log.debug("representations: {}".format(representations))

    def _ffmpeg_trim_seqment(self, input_file_path, otio_range):
        """
        Trim seqment of video file.

        Using ffmpeg to trim video to desired length.

        Args:
            input_file_path (str): path string
            otio_range (opentime.TimeRange): range to trim to

        """
        # get rendering app path
        ffmpeg_path = openpype.lib.get_ffmpeg_tool_path("ffmpeg")

        # create path to destination
        output_path = self._get_ffmpeg_output(input_file_path)

        # start command list
        command = [ffmpeg_path]

        video_path = input_file_path
        frame_start = otio_range.start_time.value
        input_fps = otio_range.start_time.rate
        frame_duration = (otio_range.duration.value + 1)
        sec_start = openpype.lib.frames_to_secons(frame_start, input_fps)
        sec_duration = openpype.lib.frames_to_secons(frame_duration, input_fps)

        # form command for rendering gap files
        command.extend([
            "-ss", str(sec_start),
            "-t", str(sec_duration),
            "-i", video_path,
            "-c", "copy",
            output_path
        ])

        # execute
        self.log.debug("Executing: {}".format(" ".join(command)))
        output = openpype.api.run_subprocess(
            command, logger=self.log
        )
        self.log.debug("Output: {}".format(output))

        return os.path.basename(output_path)

    def _get_ffmpeg_output(self, file_path):
        """
        Returning ffmpeg output command arguments.

        Arguments"
            file_path (str): path string

        Returns:
            str: output_path is path

        """
        basename = os.path.basename(file_path)
        name, ext = os.path.splitext(basename)

        output_file = "{}_{}{}".format(
            name,
            "trimmed",
            ext
        )
        # create path to destination
        return os.path.join(self.staging_dir, output_file)
