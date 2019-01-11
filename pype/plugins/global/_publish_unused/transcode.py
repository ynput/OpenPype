import os
import subprocess

import pyblish.api
import filelink


class ExtractTranscode(pyblish.api.InstancePlugin):
    """Extracts review movie from image sequence.

    Offset to get images to transcode from.
    """

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Transcode"
    optional = True
    families = ["review"]

    def find_previous_index(self, index, indexes):
        """Finds the closest previous value in a list from a value."""

        data = []
        for i in indexes:
            if i >= index:
                continue
            data.append(index - i)

        return indexes[data.index(min(data))]

    def process(self, instance):

        if "collection" in instance.data.keys():
            self.process_image(instance)

        if "output_path" in instance.data.keys():
            self.process_movie(instance)

    def process_image(self, instance):

        collection = instance.data.get("collection", [])

        if not list(collection):
            msg = "Skipping \"{0}\" because no frames was found."
            self.log.warning(msg.format(instance.data["name"]))
            return

        # Temporary fill the missing frames.
        missing = collection.holes()
        if not collection.is_contiguous():
            pattern = collection.format("{head}{padding}{tail}")
            for index in missing.indexes:
                dst = pattern % index
                src_index = self.find_previous_index(
                    index, list(collection.indexes)
                )
                src = pattern % src_index

                filelink.create(src, dst)

        # Generate args.
        # Has to be yuv420p for compatibility with older players and smooth
        # playback. This does come with a sacrifice of more visible banding
        # issues.
        # -crf 18 is visually lossless.
        args = [
            "ffmpeg", "-y",
            "-start_number", str(min(collection.indexes)),
            "-framerate", str(instance.context.data["framerate"]),
            "-i", collection.format("{head}{padding}{tail}"),
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-timecode", "00:00:00:01",
            "-vframes",
            str(max(collection.indexes) - min(collection.indexes) + 1),
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        ]

        if instance.data.get("baked_colorspace_movie"):
            args = [
                "ffmpeg", "-y",
                "-i", instance.data["baked_colorspace_movie"],
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-timecode", "00:00:00:01",
            ]

        args.append(collection.format("{head}.mov"))

        self.log.debug("Executing args: {0}".format(args))

        # Can't use subprocess.check_output, cause Houdini doesn't like that.
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            cwd=os.path.dirname(args[-1])
        )

        output = p.communicate()[0]

        # Remove temporary frame fillers
        for f in missing:
            os.remove(f)

        if p.returncode != 0:
            raise ValueError(output)

        self.log.debug(output)

    def process_movie(self, instance):
        # Generate args.
        # Has to be yuv420p for compatibility with older players and smooth
        # playback. This does come with a sacrifice of more visible banding
        # issues.
        args = [
            "ffmpeg", "-y",
            "-i", instance.data["output_path"],
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-timecode", "00:00:00:01",
        ]

        if instance.data.get("baked_colorspace_movie"):
            args = [
                "ffmpeg", "-y",
                "-i", instance.data["baked_colorspace_movie"],
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-timecode", "00:00:00:01",
            ]

        split = os.path.splitext(instance.data["output_path"])
        args.append(split[0] + "_review.mov")

        self.log.debug("Executing args: {0}".format(args))

        # Can't use subprocess.check_output, cause Houdini doesn't like that.
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
