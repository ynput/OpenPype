import os

import hiero

from pyblish import api

import pype


class ExtractFrames(pype.api.Extractor):
    """Extracts frames"""

    order = api.ExtractorOrder
    label = "Extract Frames"
    hosts = ["hiero"]
    families = ["frame"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        output_template = os.path.join(staging_dir, instance.data["name"])
        sequence = hiero.ui.activeSequence()
        files = []
        for frame in instance.data["frames"]:
            track_item = sequence.trackItemAt(frame)
            media_source = track_item.source().mediaSource()
            input_path = media_source.fileinfos()[0].filename()
            frame = track_item.mapTimelineToSource(frame)
            position = frame / sequence.framerate().toFloat()
            format = instance.data["format"]
            output_path = output_template
            output_path += ".{:04d}.{}".format(int(frame), format)
            args = [
                "ffmpeg",
                "-ss", str(position),
                "-i", input_path,
                "-vframes", "1",
                output_path
            ]
            pype.api.subprocess(args)
            files.append(output_path)

        if len(files) == 1:
            instance.data["representations"] = [
                {
                    "name": "png",
                    "ext": "png",
                    "files": os.path.basename(files[0]),
                    "stagingDir": staging_dir
                }
            ]
        else:
            instance.data["representations"] = [
                {
                    "name": "png",
                    "ext": "png",
                    "files": [os.path.basename(x) for x in files],
                    "stagingDir": staging_dir
                }
            ]
