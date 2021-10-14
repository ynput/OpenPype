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
        output_template = (
            os.path.join(staging_dir, instance.data["name"]) +
            ".{:04d}.{}"
        )
        sequence = hiero.ui.activeSequence()
        files = []
        for frame in instance.data["frames"]:
            # Convert to uncompressed exr with oiiotool.
            track_item = sequence.trackItemAt(frame)
            media_source = track_item.source().mediaSource()
            input_path = media_source.fileinfos()[0].filename()
            input_frame = (
                track_item.mapTimelineToSource(frame) +
                track_item.source().mediaSource().startTime()
            )
            exr_output_path = output_template.format(int(frame), "exr")

            args = [os.getenv("PYPE_OIIO_PATH")]

            ext = os.path.splitext(input_path)[1][1:]
            if ext in self.movie_extensions:
                args.extend(["--subimage", str(int(input_frame))])
            else:
                args.extend(["--frames", str(int(input_frame))])

            args.extend(
                [input_path, "--compression", "none", "-o", exr_output_path]
            )
            self.log.info(args)
            output = pype.api.subprocess(args)

            failed_output = "oiiotool produced no output."
            if failed_output in output:
                raise ValueError(
                    "oiiotool processing failed. Args: {}".format(args)
                )

            # Produce final format with ffmpeg.
            output_path = output_template.format(
                int(frame), instance.data["format"]
            )
            args = ["ffmpeg"]

            if input_path.endswith(".exr"):
                args.extend(["-gamma", "2.2"])

            args.extend(["-i", exr_output_path, output_path])

            self.log.info(args)
            pype.api.subprocess(args)

            files.append(output_path)

            # Clean up temporary uncompressed exr.
            os.remove(exr_output_path)

            # Feedback to user because "oiiotool" can make the publishing
            # appear unresponsive.
            self.log.info(
                "Processed {} of {} frames".format(
                    instance.data["frames"].index(frame) + 1,
                    len(instance.data["frames"])
                )
            )

        representation = {
            "name": instance.data["format"],
            "ext": instance.data["format"],
            "stagingDir": staging_dir
        }

        if len(files) == 1:
            representation["files"] = os.path.basename(files[0])
        else:
            representation["files"] = [os.path.basename(x) for x in files]

        instance.data["representations"] = [representation]
