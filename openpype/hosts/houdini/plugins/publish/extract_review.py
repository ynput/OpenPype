import os

import pyblish.api
import openpype.api
from openpype.hosts.houdini.api.lib import render_rop


class ExtractOpenGL(openpype.api.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract OpenGL (Review)"
    families = ["review"]
    hosts = ["houdini"]
    optional = True

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        output = ropnode.evalParm("picture")
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        # We run the render
        self.log.info("Extracting '%s' to '%s'" % (file_name, staging_dir))
        render_rop(ropnode)

        # Unfortunately user interrupting the extraction does not raise an
        # error and thus still continues to the integrator. To capture that
        # we make sure all files exist
        files = instance.data["frames"]
        missing = [fname for fname in files
                   if not os.path.exists(os.path.join(staging_dir, fname))]
        if missing:
            raise RuntimeError("Failed to complete review extraction. "
                               "Missing output files: {}".format(missing))

        representation = {
            "name": "png",
            "ext": "png",
            "files": files,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "tags": ["review"]
        }

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)
