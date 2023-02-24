import os
import pyblish.api

from openpype.lib import (
    get_oiio_tools_path,
    run_subprocess,
)
from openpype.pipeline import publish
from openpype.lib.applications import ApplicationManager

from subprocess import Popen, PIPE, call
def nuke_transcode_template(output_ext, input_frame, first_frame, last_frame, read_path, write_path, src_colorspace, dst_colorspace):
    python_template = '/home/jbeaulieu/dev/hiero/nuke_transcode.py'
    nuke_template = '/home/jbeaulieu/dev/hiero/ingest_transcode.nk'
    app_manager = ApplicationManager()
    nuke_app = app_manager.applications.get('nuke/14-02')
    nuke_args = nuke_app.find_executable().as_args()
    cmd = nuke_args + ['-t', python_template, nuke_template, '{0}_{1}_{2}'.format(first_frame, last_frame, input_frame), output_ext, read_path, write_path, src_colorspace, dst_colorspace]
    proc = Popen(
            cmd,
            stdout=PIPE,
            stderr=PIPE,
            env=os.environ
        )
    out, err =  proc.communicate()
    return not ('error: ' in str(err).lower() or 'Traceback' in str(err))

class TranscodeFrames(publish.Extractor):
    """Transcode frames"""

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Transcode Frames"
    hosts = ["hiero"]
    families = ["plate"]
    movie_extensions = ["mov", "mp4", 'mxf']

    def process(self, instance):
        """
        Plate - transcodes to - exr
        Reference - transcodes to - jpg

        """
        oiio_tool_path = get_oiio_tools_path()

        staging_dir = self.staging_dir(instance)
        output_template = os.path.join(staging_dir, instance.data["name"])
        output_dir = os.path.dirname(output_template)
        handle_start = instance.data['handleStart']
        handle_end = instance.data['handleEnd']
        first_frame = instance.data['frameStart']
        end_frame = instance.data['frameEnd']
        track_item = instance.data['item']


        clip_source_in = track_item.sourceIn()
        source_start = track_item.source().sourceIn()
        source_end = track_item.source().sourceOut()
        media_source = track_item.source().mediaSource()
        input_path = media_source.fileinfos()[0].filename()
        source_ext = os.path.splitext(input_path)[1][1:]
        src_colorspace = track_item.sourceMediaColourTransform()
        dst_colorspace = 'scene_linear'

        files = []
        output_ext = 'exr'
        frames = range(first_frame, end_frame+handle_start+handle_end+1)
        for frame in frames:
            input_frame = source_start + clip_source_in - handle_start + frame - first_frame
            if not input_frame >= 0 or input_frame >= source_end:
                print('Frame out of range of source - Skipping frame "{0}" - Source frame "{1}"'.format(frame, input_frame))
                continue

            output_path = output_template
            output_path += ".{:04d}.{}".format(int(frame), output_ext)
            # Only if input and output aren't video can OIIO be ran
            if output_ext.lower() in ['mxf', 'mov', 'mp4'] or source_ext.lower() in ['mxf', 'mov', 'mp4']:
                output = nuke_transcode_template(output_ext, int(input_frame), int(frame), int(frame), input_path, output_path, src_colorspace, dst_colorspace)
                if not output:
                    raise ValueError("Nuke transcode processing failed.")

            # Use OIIO instead of Nuke for faster transcoding
            else:
                args = [oiio_tool_path]

                # Input frame start
                if source_ext in self.movie_extensions:
                    args.extend(["--subimage", str(int(input_frame))])
                else:
                    args.extend(["--frames", str(int(input_frame))])

                # Input path
                args.append(input_path)

                # Add colorspace conversion
                args.extend(['--colorconvert', src_colorspace, dst_colorspace])

                # Copy old metadata
                args.append('--pastemeta')

                # Add metadata
                # Ingest colorspace
                args.extend(['--sattrib', 'akemy/ingest/colorspace', src_colorspace])
                # Input Fileline
                args.extend(['--sattrib', 'input/filename', input_path])

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
            representation_exts = [rep['ext'] for rep in instance.data["representations"]]
            representation_ext_index = representation_exts.index(source_ext)
            if source_ext in representation_exts:
                print('Removing source representation and replacing with transcoded frames')
                instance.data["representations"].pop(representation_ext_index)
            else:
                print('No source ext to remove from representation')
        except:
            print('Failed to remove source ext "{0}" from representations'.format(source_ext))

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
