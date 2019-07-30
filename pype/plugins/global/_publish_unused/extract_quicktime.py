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

    label = "Extract Quicktime"
    order = pyblish.api.ExtractorOrder
    families = ["imagesequence", "render", "write", "source"]
    hosts = ["shell"]

    def process(self, instance):
        # fps = instance.data.get("fps")
        # start = instance.data.get("startFrame")
        # stagingdir = os.path.normpath(instance.data.get("stagingDir"))
        #
        # collected_frames = os.listdir(stagingdir)
        # collections, remainder = clique.assemble(collected_frames)
        #
        # full_input_path = os.path.join(
        #     stagingdir, collections[0].format('{head}{padding}{tail}')
        # )
        # self.log.info("input {}".format(full_input_path))
        #
        # filename = collections[0].format('{head}')
        # if not filename.endswith('.'):
        #     filename += "."
        # movFile = filename + "mov"
        # full_output_path = os.path.join(stagingdir, movFile)
        #
        # self.log.info("output {}".format(full_output_path))
        #
        # config_data = instance.context.data['output_repre_config']
        #
        # proj_name = os.environ.get('AVALON_PROJECT', '__default__')
        # profile = config_data.get(proj_name, config_data['__default__'])
        #
        # input_args = []
        # # overrides output file
        # input_args.append("-y")
        # # preset's input data
        # input_args.extend(profile.get('input', []))
        # # necessary input data
        # input_args.append("-start_number {}".format(start))
        # input_args.append("-i {}".format(full_input_path))
        # input_args.append("-framerate {}".format(fps))
        #
        # output_args = []
        # # preset's output data
        # output_args.extend(profile.get('output', []))
        # # output filename
        # output_args.append(full_output_path)
        # mov_args = [
        #     "ffmpeg",
        #     " ".join(input_args),
        #     " ".join(output_args)
        # ]
        # subprocess_mov = " ".join(mov_args)
        # sub_proc = subprocess.Popen(subprocess_mov)
        # sub_proc.wait()
        #
        # if not os.path.isfile(full_output_path):
        #     raise("Quicktime wasn't created succesfully")
        #
        # if "representations" not in instance.data:
        #     instance.data["representations"] = []
        #
        # representation = {
        #     'name': 'mov',
        #     'ext': 'mov',
        #     'files': movFile,
        #     "stagingDir": stagingdir,
        #     "preview": True
        # }
        # instance.data["representations"].append(representation)
