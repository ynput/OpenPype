import os
import pyblish
import openpype.api
from openpype.lib import (
    get_ffmpeg_tool_path,
    path_to_subprocess_arg
)
import tempfile
import opentimelineio as otio


class ExtractOtioAudioTracks(pyblish.api.ContextPlugin):
    """Extract Audio tracks from OTIO timeline.

    Process will merge all found audio tracks into one long .wav file at frist
    stage. Then it will trim it into individual short audio files relative to
    asset length and add it to each marked instance data representation. This
    is influenced by instance data audio attribute """

    order = pyblish.api.ExtractorOrder - 0.44
    label = "Extract OTIO Audio Tracks"
    hosts = ["hiero", "resolve", "flame"]

    # FFmpeg tools paths
    ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")

    def process(self, context):
        """Convert otio audio track's content to audio representations

        Args:
            context (pyblish.Context): context of publisher
        """
        # split the long audio file to peces devided by isntances
        audio_instances = self.get_audio_instances(context)
        self.log.debug("Audio instances: {}".format(len(audio_instances)))

        if len(audio_instances) < 1:
            self.log.info("No audio instances available")
            return

        # get sequence
        otio_timeline = context.data["otioTimeline"]

        # get all audio inputs from otio timeline
        audio_inputs = self.get_audio_track_items(otio_timeline)

        if not audio_inputs:
            return

        # temp file
        audio_temp_fpath = self.create_temp_file("audio")

        # create empty audio with longest duration
        empty = self.create_empty(audio_inputs)

        # add empty to list of audio inputs
        audio_inputs.insert(0, empty)

        # create cmd
        cmd = path_to_subprocess_arg(self.ffmpeg_path) + " "
        cmd += self.create_cmd(audio_inputs)
        cmd += path_to_subprocess_arg(audio_temp_fpath)

        # run subprocess
        self.log.debug("Executing: {}".format(cmd))
        openpype.api.run_subprocess(
            cmd, shell=True, logger=self.log
        )

        # remove empty
        os.remove(empty["mediaPath"])

        # cut instance framerange and add to representations
        self.add_audio_to_instances(audio_temp_fpath, audio_instances)

        # remove full mixed audio file
        os.remove(audio_temp_fpath)

    def add_audio_to_instances(self, audio_file, instances):
        created_files = []
        for inst in instances:
            name = inst.data["asset"]

            recycling_file = [f for f in created_files if name in f]

            # frameranges
            timeline_in_h = inst.data["clipInH"]
            timeline_out_h = inst.data["clipOutH"]
            fps = inst.data["fps"]

            # create duration
            duration = (timeline_out_h - timeline_in_h) + 1

            # ffmpeg generate new file only if doesnt exists already
            if not recycling_file:
                # convert to seconds
                start_sec = float(timeline_in_h / fps)
                duration_sec = float(duration / fps)

                # temp audio file
                audio_fpath = self.create_temp_file(name)

                cmd = [
                    self.ffmpeg_path,
                    "-ss", str(start_sec),
                    "-t", str(duration_sec),
                    "-i", audio_file,
                    audio_fpath
                ]

                # run subprocess
                self.log.debug("Executing: {}".format(" ".join(cmd)))
                openpype.api.run_subprocess(
                    cmd, logger=self.log
                )
            else:
                audio_fpath = recycling_file.pop()

            if "audio" in (inst.data["families"] + [inst.data["family"]]):
                # create empty representation attr
                if "representations" not in inst.data:
                    inst.data["representations"] = []
                # add to representations
                inst.data["representations"].append({
                    "files": os.path.basename(audio_fpath),
                    "name": "wav",
                    "ext": "wav",
                    "stagingDir": os.path.dirname(audio_fpath),
                    "frameStart": 0,
                    "frameEnd": duration
                })

            elif "reviewAudio" in inst.data.keys():
                audio_attr = inst.data.get("audio") or []
                audio_attr.append({
                    "filename": audio_fpath,
                    "offset": 0
                })
                inst.data["audio"] = audio_attr

            # add generated audio file to created files for recycling
            if audio_fpath not in created_files:
                created_files.append(audio_fpath)

    def get_audio_instances(self, context):
        """Return only instances which are having audio in families

        Args:
            context (pyblish.context): context of publisher

        Returns:
            list: list of selected instances
        """
        return [
            _i for _i in context
            # filter only those with audio family
            # and also with reviewAudio data key
            if bool("audio" in (
                _i.data.get("families", []) + [_i.data["family"]])
            ) or _i.data.get("reviewAudio")
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
        cmd = [
            self.ffmpeg_path,
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", str(max_duration_sec),
            empty_fpath
        ]

        # generate empty with ffmpeg
        # run subprocess
        self.log.debug("Executing: {}".format(" ".join(cmd)))

        openpype.api.run_subprocess(
            cmd, logger=self.log
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
            input_format["mediaPath"] = path_to_subprocess_arg(
                input_format["mediaPath"]
            )

            _inputs += (
                "-ss {startSec} "
                "-t {durationSec} "
                "-i {mediaPath} "
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
