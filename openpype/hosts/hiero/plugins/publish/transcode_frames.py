import os
import pyblish.api

from openpype.lib import (
    get_oiio_tools_path,
    run_subprocess,
)
from openpype.pipeline import publish
from openpype.lib.applications import ApplicationManager


def nuke_transcode_template(output_ext, input_frame, first_frame, last_frame, read_path, write_path, src_colorspace, dst_colorspace):
    python_template = "/pipe/hiero/templates/nuke_transcode.py"
    nuke_template = "/pipe/hiero/templates/ingest_transcode.nk"
    app_manager = ApplicationManager()
    nuke_app = app_manager.applications.get("nuke/14-02")
    nuke_args = nuke_app.find_executable().as_args()
    cmd = nuke_args + ["-t", python_template, nuke_template, "{0}_{1}_{2}".format(first_frame, last_frame, input_frame), output_ext, read_path, write_path, src_colorspace, dst_colorspace]

    # If non exist status is returned output will raise exception.
    # No need to handle since run_subprocess already formats and handles error
    run_subprocess(cmd)


def openpype_publish_tag(track_item, instance_tags):
    """
    Get tag that was used to publish track item
    """
    for instance_tag in instance_tags:
        t_metadata = dict(instance_tag.metadata())
        t_family = t_metadata.get("tag.family", "")
        if t_family == "plate":
            for item_tag in track_item.tags():
                if instance_tag.name() == item_tag.name():
                    return dict(item_tag.metadata())

    return {}


def get_tag_handles(track_item, instance_tags):
    tag = openpype_publish_tag(track_item, instance_tags)
    try:
        handle_start = int(tag.get("tag.handleStart", "0"))
        handle_end = int(tag.get("tag.handleEnd", "0"))
    except ValueError:
        raise Exception("Handle field should only contain numbers")

    return handle_start, handle_end


class TranscodeFrames(publish.Extractor):
    """Transcode frames"""

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Transcode Frames"
    hosts = ["hiero"]
    families = ["plate"]

    def process(self, instance):
        """
        Plate - Transcodes to exr with color becoming linear
        Reference - For now does not get transcoded and stays same as source
        """
        oiio_tool_path = get_oiio_tools_path()

        staging_dir = self.staging_dir(instance)
        output_template = os.path.join(staging_dir, instance.data["name"])
        output_dir = os.path.dirname(output_template)
        instance_tags = instance.data["tags"]
        track_item = instance.data["item"]
        media_source = track_item.source().mediaSource()

        # Define frame output range
        # handleStart and handleEnd are overriden to reflect media range and not absolute handles
        # Solution is to take the handle values directly from the tag instead of instance data
        handle_start, handle_end = get_tag_handles(track_item, instance_tags)
        first_frame = instance.data["frameStart"]
        end_frame = instance.data["frameEnd"] + handle_end

        # Need clip source in and original clip source media in and out to calculate matching input frame
        clip_source_in = track_item.sourceIn()
        source_start = track_item.source().sourceIn()
        source_end = track_item.source().sourceOut()

        # Define source path along with extension
        input_path = media_source.fileinfos()[0].filename()
        source_ext = os.path.splitext(input_path)[1][1:]

        # Determine color transformation
        src_colorspace = track_item.sourceMediaColourTransform()
        dst_colorspace = "scene_linear"

        files = []
        movie_extensions = {"mov", "mp4", "mxf"}
        output_ext = "exr"
        frames = range(first_frame, end_frame + handle_start + 1)
        self.log.info('Trancoding frame range {0} - {1}'.format(frames[0], frames[-1]))
        for frame in frames:
            # Calculate input_frame for output by normalizing input media to first frame
            input_frame = source_start + clip_source_in - handle_start + frame - first_frame
            if not input_frame >= 1 or input_frame >= source_end + 1:
                self.log.warning("Frame out of range of source - Skipping frame '{0}' - Source frame '{1}'".format(frame, input_frame))
                continue

            output_path = output_template
            output_path += ".{:04d}.{}".format(int(frame), output_ext)
            # If either source or output is a video format, transcode using Nuke
            if output_ext.lower() in movie_extensions or source_ext.lower() in movie_extensions:
                # No need to raise error as Nuke raises an error exit value if something went wrong
                nuke_transcode_template(output_ext, int(input_frame), int(frame), int(frame), input_path, output_path, src_colorspace, dst_colorspace)

            # Else use OIIO instead of Nuke for faster transcoding
            else:
                args = [oiio_tool_path]

                # Input frame start
                args.extend(["--frames", str(int(input_frame))])

                # Input path
                args.append(input_path)

                # Add colorspace conversion
                args.extend(["--colorconvert", src_colorspace, dst_colorspace])

                # Copy old metadata
                args.append("--pastemeta")

                # Add metadata
                # Ingest colorspace
                args.extend(["--sattrib", "alkemy/ingest/colorspace", src_colorspace])
                # Input Filename
                args.extend(["--sattrib", "input/filename", input_path])

                # Output path
                args.extend(["-o", output_path])

                output = run_subprocess(args)

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
                    frames.index(frame) + 1,
                    len(frames)
                )
            )

        try:
            representation_exts = [rep["ext"] for rep in instance.data["representations"]]
            representation_ext_index = representation_exts.index(source_ext)
            if source_ext in representation_exts:
                self.log.info("Removing source representation and replacing with transcoded frames")
                instance.data["representations"].pop(representation_ext_index)
            else:
                self.log.info("No source ext to remove from representation")
        except IndexError:
            self.log.warning("Failed to remove source ext '{0}' from representations".format(source_ext))

        if len(files) == 1:
            instance.data["representations"].append(
                {
                    "name": output_ext,
                    "ext": output_ext,
                    "files": os.path.basename(files[0]),
                    "stagingDir": output_dir
                }
            )
        else:
            instance.data["representations"].append(
                {
                    "name": output_ext,
                    "ext": output_ext,
                    "files": [os.path.basename(x) for x in files],
                    "stagingDir": output_dir
                }
            )
