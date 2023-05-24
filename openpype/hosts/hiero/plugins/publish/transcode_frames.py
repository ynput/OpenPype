import os
import pyblish.api

from openpype.lib import (
    get_oiio_tools_path,
    run_subprocess,
)
from openpype.pipeline import publish
from openpype.lib.applications import ApplicationManager


def nuke_transcode_template(
    output_ext,
    input_frame,
    first_frame,
    last_frame,
    read_path,
    write_path,
    src_colorspace,
    dst_colorspace,
):
    python_template = "/pipe/hiero/templates/nuke_transcode.py"
    nuke_template = "/pipe/hiero/templates/ingest_transcode.nk"
    app_manager = ApplicationManager()
    nuke_app_name = os.environ["AVALON_APP_NAME"].replace("hiero", "nuke")
    nuke_app = app_manager.applications.get(nuke_app_name)
    nuke_args = nuke_app.find_executable().as_args()
    cmd = nuke_args + [
        "-t",
        python_template,
        nuke_template,
        "{0}_{1}_{2}".format(int(first_frame), int(last_frame), int(input_frame)),
        output_ext,
        read_path,
        write_path,
        src_colorspace,
        dst_colorspace,
    ]

    # If non exist status is returned output will raise exception.
    # No need to handle since run_subprocess already formats and handles error
    run_subprocess(cmd)


class TranscodeFrames(publish.Extractor):
    """Transcode frames"""

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Transcode Frames"
    hosts = ["hiero"]
    families = ["plate"]
    movie_extensions = {"mov", "mp4", "mxf"}
    output_ext = "exr"
    dst_colorspace = "scene_linear"

    def process(self, instance):
        """
        Plate - Transcodes to exr with color becoming linear
        Reference - For now does not get transcoded and stays same as source
        """
        oiio_tool_path = get_oiio_tools_path()

        track_item = instance.data["item"]
        media_source = track_item.source().mediaSource()

        # Define source path along with extension
        input_path = media_source.fileinfos()[0].filename()
        source_ext = os.path.splitext(input_path)[1][1:]

        # Output variables
        staging_dir = self.staging_dir(instance)
        output_template = os.path.join(staging_dir, instance.data["name"])
        output_dir = os.path.dirname(output_template)

        # Determine color transformation
        src_colorspace = track_item.sourceMediaColourTransform()

        frame_range = instance.data["frameRange"]
        len_frames = len(frame_range)
        files = []
        for index, (input_frame, output_frame) in enumerate(frame_range):
            output_path = f"{output_template}.{output_frame:04d}.{self.output_ext}"
            # If either source or output is a video format, transcode using Nuke
            if (
                self.output_ext.lower() in self.movie_extensions
                or source_ext.lower() in self.movie_extensions
            ):
                # No need to raise error as Nuke raises an error exit value if something went wrong
                nuke_transcode_template(
                    self.output_ext,
                    input_frame,
                    output_frame,
                    output_frame,
                    input_path,
                    output_path,
                    src_colorspace,
                    self.dst_colorspace,
                )

            # Else use OIIO instead of Nuke for faster transcoding
            else:
                args = [oiio_tool_path]

                # Input frame start
                args.extend(["--frames", str(int(input_frame))])

                # Input path
                args.append(input_path)

                # Add colorspace conversion
                args.extend(["--colorconvert", src_colorspace, self.dst_colorspace])

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
                    raise ValueError("oiiotool processing failed. Args: {}".format(args))

            files.append(output_path)

            # Feedback to user because "oiiotool" can make the publishing
            # appear unresponsive.
            self.log.info("Processed {} of {} frames".format(index + 1, len_frames))

        ext_representations = [
            rep for rep in instance.data["representations"] if rep["ext"] == source_ext
        ]
        if ext_representations:
            self.log.info("Removing source representation and replacing with transcoded frames")
            instance.data["representations"].remove(ext_representations[0])
        else:
            self.log.info("No source ext to remove from representation")

        instance.data["representations"].append(
            {
                "name": self.output_ext,
                "ext": self.output_ext,
                "files": os.path.basename(files[0])
                if len(files) == 1
                else [os.path.basename(x) for x in files],
                "stagingDir": output_dir,
                ### Starts Alkemy-X Override ###
                # After EXRs are processed - review needs be added to the new
                # representation
                "tags": ["review"],
                ### Ends Alkemy-X Override ###
            }
        )
