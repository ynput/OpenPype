import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop

import hou


class ExtractVDBCache(publish.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    families = ["vdbcache"]
    hosts = ["houdini"]

    def process(self, instance):
        if instance.data.get("farm"):
            self.log.debug("Should be processed on farm, skipping.")
            return
        ropnode = hou.node(instance.data["instance_node"])

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        sop_output = ropnode.evalParm("sopoutput")
        staging_dir = os.path.normpath(os.path.dirname(sop_output))
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(sop_output)

        self.log.info("Writing VDB '%s' to '%s'" % (file_name, staging_dir))

        render_rop(ropnode)

        output = instance.data["frames"]

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "vdb",
            "ext": "vdb",
            "files": output,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"],
        }
        instance.data["representations"].append(representation)
