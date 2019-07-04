import os
import subprocess

from hiero.exporters.FnExportUtil import writeSequenceAudioWithHandles

import pype.api


class ExtractReview(pype.api.Extractor):
    """Extract Quicktime with optimized codec for reviewing."""

    label = "Review"
    hosts = ["nukestudio"]
    families = ["review"]
    optional = True

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        filename = "{0}_without_sound".format(instance.name) + ".mov"
        output_path = os.path.join(staging_dir, filename)
        input_path = instance.data["sourcePath"]
        item = instance.data["item"]

        # Has to be yuv420p for compatibility with older players and smooth
        # playback. This does come with a sacrifice of more visible banding
        # issues.
        start_frame = item.mapTimelineToSource(item.timelineIn())
        end_frame = item.mapTimelineToSource(item.timelineOut())
        args = [
            "ffmpeg",
            "-ss", str(start_frame / item.sequence().framerate().toFloat()),
            "-i", input_path,
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-timecode", "00:00:00:01",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-frames", str(int(end_frame - start_frame) + 1),
            output_path
        ]

        self.log.debug(subprocess.list2cmdline(args))
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            cwd=os.path.dirname(args[-1])
        )

        output = p.communicate()[0]

        if p.returncode != 0:
            raise ValueError(output)

        self.log.debug(output)

        # Extract audio.
        filename = "{0}".format(instance.name) + ".wav"
        audio_path = os.path.join(staging_dir, filename)
        writeSequenceAudioWithHandles(
            audio_path,
            item.sequence(),
            item.timelineIn(),
            item.timelineOut(),
            0,
            0
        )

        input_path = output_path
        filename = "{0}_with_sound".format(instance.name) + ".mov"
        output_path = os.path.join(staging_dir, filename)

        args = [
            "ffmpeg",
            "-i", input_path,
            "-i", audio_path,
            "-vcodec", "copy",
            output_path
        ]

        self.log.debug(subprocess.list2cmdline(args))
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            cwd=os.path.dirname(args[-1])
        )

        output = p.communicate()[0]

        if p.returncode != 0:
            raise ValueError(output)

        self.log.debug(output)

        # Adding movie representation.
        start_frame = int(
            instance.data["sourceIn"] - (
                instance.data["handleStart"] + instance.data["handles"]
            )
        )
        end_frame = int(
            instance.data["sourceOut"] + (
                instance.data["handleEnd"] + instance.data["handles"]
            )
        )
        representation = {
            "files": os.path.basename(output_path),
            "staging_dir": staging_dir,
            "startFrame": 0,
            "endFrame": end_frame - start_frame,
            "step": 1,
            "frameRate": (
                instance.context.data["activeSequence"].framerate().toFloat()
            ),
            "preview": True,
            "thumbnail": False,
            "name": "preview",
            "ext": "mov",
        }
        instance.data["representations"] = [representation]
        self.log.debug("Adding representation: {}".format(representation))

        # Adding thumbnail representation.
        path = instance.data["sourcePath"].replace(".mov", ".png")
        if not os.path.exists(path):
            item.thumbnail(start_frame).save(path, format="png")

        representation = {
            "files": os.path.basename(path),
            "stagingDir": os.path.dirname(path),
            "name": "thumbnail",
            "thumbnail": True,
            "ext": "png"
        }
        instance.data["representations"].append(representation)
        self.log.debug("Adding representation: {}".format(representation))
