import os
import pyblish.api
import subprocess
from pype.vendor import clique


class ExtractJpegEXR(pyblish.api.InstancePlugin):
    """Resolve any dependency issies

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.
    """

    label = "Extract Jpeg EXR"
    order = pyblish.api.ExtractorOrder
    families = ["imagesequence", "render", "write", "source"]
    host = ["shell"]

    def process(self, instance):
        start = instance.data.get("startFrame")
        stagingdir = os.path.normpath(instance.data.get("stagingDir"))

        collected_frames = os.listdir(stagingdir)
        collections, remainder = clique.assemble(collected_frames)

        input_file = (
            collections[0].format('{head}{padding}{tail}') % start
        )
        full_input_path = os.path.join(stagingdir, input_file)
        self.log.info("input {}".format(full_input_path))

        filename = collections[0].format('{head}')
        if not filename.endswith('.'):
            filename += "."
        jpegFile = filename + "jpg"
        full_output_path = os.path.join(stagingdir, jpegFile)

        self.log.info("output {}".format(full_output_path))

        subprocess_jpeg = "ffmpeg -y -gamma 2.2 -i {} {}".format(
            full_input_path, full_output_path
        )
        subprocess.Popen(subprocess_jpeg)

        if "files" not in instance.data:
            instance.data["files"] = list()
        instance.data["files"].append(jpegFile)
