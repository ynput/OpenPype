import os

import pype.api

from pype.vendor import ffmpeg


class ExtractPlate(pype.api.Extractor):
    """Extract plate cut to the timeline.

    Only supporting mov plates for now. Image sequences already get cut down to
    timeline range.

    """

    label = "Plate"
    hosts = ["nukestudio"]
    families = ["plate"]
    optional = True

    def process(self, instance):
        if not instance.data["sourcePath"].endswith(".mov"):
            self.log.debug(
                "Skipping {} because its not a \"*.mov\" "
                "format.".format(instance)
            )
            return

        staging_dir = self.staging_dir(instance)
        filename = "{0}".format(instance.name) + ".mov"
        output_path = os.path.join(staging_dir, filename)
        input_path = instance.data["sourcePath"]

        self.log.info("Outputting movie to %s" % output_path)

        # Cut plate to timeline.
        item = instance.data["item"]
        start_frame = item.mapTimelineToSource(
            item.timelineIn() - (
                instance.data["handleStart"] + instance.data["handles"]
            )
        )
        end_frame = item.mapTimelineToSource(
            item.timelineOut() + (
                instance.data["handleEnd"] + instance.data["handles"]
            )
        )
        framerate = item.sequence().framerate().toFloat()
        output_options = {
            "vcodec": "copy",
            "ss": start_frame / framerate,
            "frames": int(end_frame - start_frame) + 1
        }

        try:
            (
                ffmpeg
                .input(input_path)
                .output(output_path, **output_options)
                .run(overwrite_output=True,
                     capture_stdout=True,
                     capture_stderr=True)
            )
        except ffmpeg.Error as e:
            ffmpeg_error = "ffmpeg error: {}".format(e.stderr)
            self.log.error(ffmpeg_error)
            raise RuntimeError(ffmpeg_error)

        # Adding representation.
        ext = os.path.splitext(output_path)[1][1:]
        representation = {
            "files": os.path.basename(output_path),
            "staging_dir": staging_dir,
            "startFrame": 0,
            "endFrame": end_frame - start_frame,
            "step": 1,
            "frameRate": framerate,
            "thumbnail": False,
            "name": ext,
            "ext": ext
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
