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
    movie_extensions = ["mov"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        output_template = os.path.join(staging_dir, instance.data["name"])
        sequence = hiero.ui.activeSequence()
        files = []
        for frame in instance.data["frames"]:
            track_item = sequence.trackItemAt(frame)
            media_source = track_item.source().mediaSource()
            input_path = media_source.fileinfos()[0].filename()
            input_frame = (
                track_item.mapTimelineToSource(frame) +
                track_item.source().mediaSource().startTime()
            )
            format = instance.data["format"]
            output_path = output_template
            output_path += ".{:04d}.{}".format(int(frame), format)

            args = ["oiiotool"]

            ext = os.path.splitext(input_path)[1][1:]
            if ext in self.movie_extensions:
                args.extend(["--subimage", str(int(input_frame))])
            else:
                args.extend(["--frames", str(int(input_frame))])

            if ext == "exr":
                args.extend(["--powc", "0.45,0.45,0.45,1.0"])

            args.extend([input_path, "-o", output_path])
            output = pype.api.subprocess(args)

            failed_output = "oiiotool produced no output."
            if failed_output in output:
                raise ValueError(
                    "oiiotool processing failed. Args: {}".format(args)
                )

            files.append(output_path)

            # Feedback to user because "oiiotool" can make the publishing
            # appear unresponsive.
            self.log.info(
                "Processed {} of {} frames".format(
                    instance.data["frames"].index(frame) + 1,
                    len(instance.data["frames"])
                )
            )

        if len(files) == 1:
            instance.data["representations"] = [
                {
                    "name": format,
                    "ext": format,
                    "files": os.path.basename(files[0]),
                    "stagingDir": staging_dir
                }
            ]
        else:
            instance.data["representations"] = [
                {
                    "name": format,
                    "ext": format,
                    "files": [os.path.basename(x) for x in files],
                    "stagingDir": staging_dir
                }
            ]
