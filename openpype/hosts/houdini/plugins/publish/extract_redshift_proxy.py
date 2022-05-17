import os

import pyblish.api
import openpype.api
from openpype.hosts.houdini.api.lib import render_rop


class ExtractRedshiftProxy(openpype.api.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Redshift Proxy"
    families = ["redshiftproxy"]
    hosts = ["houdini"]

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        output = ropnode.evalParm("RS_archive_file")
        staging_dir = os.path.normpath(os.path.dirname(output))
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        self.log.info("Writing Redshift Proxy '%s' to '%s'" % (file_name,
                                                               staging_dir))

        render_rop(ropnode)

        output = instance.data["frames"]

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "rs",
            "ext": "rs",
            "files": output,
            "stagingDir": staging_dir,
        }

        # A single frame may also be rendered without start/end frame.
        if "frameStart" in instance.data and "frameEnd" in instance.data:
            representation["frameStart"] = instance.data["frameStart"]
            representation["frameEnd"] = instance.data["frameEnd"]

        instance.data["representations"].append(representation)
