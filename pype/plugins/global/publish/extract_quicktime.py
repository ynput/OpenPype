import os
import pyblish.api
import subprocess
from pype.vendor import clique


class ExtractQuicktimeEXR(pyblish.api.InstancePlugin):
    """Resolve any dependency issies

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.
    """

    label = "Extract Quicktime EXR"
    order = pyblish.api.ExtractorOrder
    families = ["imagesequence", "render", "write", "source"]
    host = ["shell"]

    def process(self, instance):
        fps = instance.data.get("fps")
        start = instance.data.get("startFrame")
        stagingdir = os.path.normpath(instance.data.get("stagingDir"))

        collected_frames = os.listdir(stagingdir)
        collections, remainder = clique.assemble(collected_frames)
        filename = collections[0].format('{head}')

        input_path = os.path.join(
            stagingdir, collections[0].format('{head}{padding}{tail}')
        )
        collections[0].format('{head}{padding}{tail}')
        self.log.info("input {}".format(input_path))
        single_file_name = (
            collections[0].format('{head}{padding}{tail}') % start
        )
        single_input_path = os.path.join(stagingdir, single_file_name)
        if not filename.endswith('.'):
            filename += "."
        movFile = filename + "mov"
        jpegFile = filename + "jpg"
        full_mov_path = os.path.join(stagingdir, movFile)
        full_jpeg_path = os.path.join(stagingdir, jpegFile)

        self.log.info("output {}".format(full_mov_path))

        subprocess_jpeg = "ffmpeg -y -gamma 2.2 -i {} {}".format(
            single_input_path, full_jpeg_path
        )
        subprocess.Popen(subprocess_jpeg)

        input_args = [
            "-y -gamma 2.2",
            "-i {}".format(input_path),
            "-framerate {}".format(fps),
            "-start_number {}".format(start)
        ]
        output_args = [
            "-c:v libx264",
            "-vf colormatrix=bt601:bt709",
            full_mov_path
        ]

        mov_args = [
            "ffmpeg",
            " ".join(input_args),
            " ".join(output_args)
        ]
        subprocess_mov = " ".join(mov_args)
        self.log.info("Mov args: {}".format(subprocess_mov))
        subprocess.Popen(subprocess_mov)

        if "files" not in instance.data:
            instance.data["files"] = list()
        # instance.data["files"].append(jpegFile)
        instance.data["files"].append(movFile)
