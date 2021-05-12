import os
import pyblish
import openpype.api
from openpype.lib import (
    get_ffmpeg_tool_path
)
import tempfile
import opentimelineio as otio


class ExtractOtioAudioTracks(pyblish.api.ContextPlugin):
    """Extract Audio tracks from OTIO timeline.

    Process will merge all found audio tracks into one long .wav file at frist
    stage. Then it will trim it into individual short audio files relative to
    asset length and add it to each marked instance data representation. This
    is influenced by instance data audio attribute """

    order = pyblish.api.CollectorOrder - 0.571
    label = "Extract OTIO Audio Tracks"
    hosts = ["hiero"]

    # FFmpeg tools paths
    ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")

    def process(self, context):
        """Convert otio audio track's content to audio representations

        Args:
            context (pyblish.Context): context of publisher
        """

        # get sequence
        otio_timeline = context.data["otioTimeline"]

        # temp file
        audio_temp_fpath = self.create_temp_file("audio")

        # get all audio inputs from otio timeline
        audio_inputs = self.get_audio_track_items(otio_timeline)

        # create empty audio with longest duration
        empty = self.create_empty(audio_inputs)

        # add empty to list of audio inputs
        audio_inputs.insert(0, empty)

        # create cmd
        cmd = self.ffmpeg_path + " "
        cmd += self.create_cmd(audio_inputs)
        cmd += audio_temp_fpath

        # run subprocess
        self.log.debug("Executing: {}".format(cmd))
        openpype.api.run_subprocess(
            cmd, shell=True, logger=self.log
        )

        # remove empty
        os.remove(empty["mediaPath"])

        # split the long audio file to peces devided by isntances
        audio_instances = self.get_audio_instances(context)

        # cut instance framerange and add to representations
        self.create_audio_representations(audio_temp_fpath, audio_instances)

    def create_audio_representations(self, audio_file, instances):
        for inst in instances:
            # create empty representation attr
            if "representations" not in inst.data:
                inst.data["representations"] = []

            name = inst.data["name"]

            # frameranges
            timeline_in_h = inst.data["clipInH"]
            timeline_out_h = inst.data["clipOutH"]
            fps = inst.data["fps"]

            # seconds
            duration = (timeline_out_h - timeline_in_h) + 1
            start_sec = float(timeline_in_h / fps)
            duration_sec = float(duration / fps)

            # temp audio file
            audio_fpath = self.create_temp_file(name)

            cmd = " ".join([
                self.ffmpeg_path,
                "-ss {}".format(start_sec),
                "-t {}".format(duration_sec),
                "-i {}".format(audio_file),
                audio_fpath
            ])

            # run subprocess
            self.log.debug("Executing: {}".format(cmd))
            openpype.api.run_subprocess(
                cmd, shell=True, logger=self.log
            )

            # add to representations
            inst.data["representations"].append({
                "files": os.path.basename(audio_fpath),
                "name": "wav",
                "ext": "wav",
                "stagingDir": os.path.dirname(audio_fpath),
                "frameStart": 0,
                "frameEnd": duration
            })

    def get_audio_instances(self, context):
        """Return only instances which are having audio in families

        Args:
            context (pyblish.context): context of publisher

        Returns:
            list: list of selected instances
        """
        return [
            _i for _i in context
            if bool("audio" in _i.data.get("families", []))
        ]

    def get_audio_track_items(self, otio_timeline):
        """Get all audio clips form OTIO audio tracks

        Args:
            otio_timeline (otio.schema.timeline): timeline object

        Returns:
            list: list of audio clip dictionaries
        """
        output = []
        # go trough all audio tracks
        for otio_track in otio_timeline.tracks:
            if "Audio" not in otio_track.kind:
                continue
            self.log.debug("_" * 50)
            playhead = 0
            for otio_clip in otio_track:
                self.log.debug(otio_clip)
                if isinstance(otio_clip, otio.schema.Gap):
                    playhead += otio_clip.source_range.duration.value
                elif isinstance(otio_clip, otio.schema.Clip):
                    start = otio_clip.source_range.start_time.value
                    duration = otio_clip.source_range.duration.value
                    fps = otio_clip.source_range.start_time.rate
                    media_path = otio_clip.media_reference.target_url
                    input = {
                        "mediaPath": media_path,
                        "delayFrame": playhead,
                        "startFrame": start,
                        "durationFrame": duration,
                        "delayMilSec": int(float(playhead / fps) * 1000),
                        "startSec": float(start / fps),
                        "durationSec": float(duration / fps),
                        "fps": fps
                    }
                    if input not in output:
                        output.append(input)
                        self.log.debug("__ input: {}".format(input))
                    playhead += otio_clip.source_range.duration.value

        return output

    def create_empty(self, inputs):
        """Create an empty audio file used as duration placeholder

        Args:
            inputs (list): list of audio clip dictionaries

        Returns:
            dict: audio clip dictionary
        """
        # temp file
        empty_fpath = self.create_temp_file("empty")

        # get all end frames
        end_secs = [(_i["delayFrame"] + _i["durationFrame"]) / _i["fps"]
                    for _i in inputs]
        # get the max of end frames
        max_duration_sec = max(end_secs)

        # create empty cmd
        cmd = " ".join([
            self.ffmpeg_path,
            "-f lavfi",
            "-i anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t {}".format(max_duration_sec),
            empty_fpath
        ])

        # generate empty with ffmpeg
        # run subprocess
        self.log.debug("Executing: {}".format(cmd))

        openpype.api.run_subprocess(
            cmd, shell=True, logger=self.log
        )

        # return dict with output
        return {
            "mediaPath": empty_fpath,
            "delayMilSec": 0,
            "startSec": 0.00,
            "durationSec": max_duration_sec
        }

    def create_cmd(self, inputs):
        """Creating multiple input cmd string

        Args:
            inputs (list): list of input dicts. Order mater.

        Returns:
            str: the command body

        """
        # create cmd segments
        _inputs = ""
        _filters = "-filter_complex \""
        _channels = ""
        for index, input in enumerate(inputs):
            input_format = input.copy()
            input_format.update({"i": index})
            _inputs += (
                "-ss {startSec} "
                "-t {durationSec} "
                "-i \"{mediaPath}\" "
            ).format(**input_format)

            _filters += "[{i}]adelay={delayMilSec}:all=1[r{i}]; ".format(
                **input_format)
            _channels += "[r{}]".format(index)

        # merge all cmd segments together
        cmd = _inputs + _filters + _channels
        cmd += str(
            "amix=inputs={inputs}:duration=first:"
            "dropout_transition=1000,volume={inputs}[a]\" "
        ).format(inputs=len(inputs))
        cmd += "-map \"[a]\" "

        return cmd

    def create_temp_file(self, name):
        """Create temp wav file

        Args:
            name (str): name to be used in file name

        Returns:
            str: temp fpath
        """
        return os.path.normpath(
            tempfile.mktemp(
                prefix="pyblish_tmp_{}_".format(name),
                suffix=".wav"
            )
        )
