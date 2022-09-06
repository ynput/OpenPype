import os

import pyblish.api
import openpype.api

from openpype.hosts.houdini.api.lib import render_rop


class ExtractComposite(openpype.api.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Composite (Image Sequence)"
    hosts = ["houdini"]
    families = ["imagesequence"]

    def process(self, instance):

        ropnode = instance.data["members"][0]

        # Get the filename from the copoutput parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        output = ropnode.evalParm("copoutput")
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        self.log.info("Writing comp '%s' to '%s'" % (file_name, staging_dir))

        render_rop(ropnode)

        if "files" not in instance.data:
            instance.data["files"] = []

        frames = instance.data["frames"]
        instance.data["files"].append(frames)
