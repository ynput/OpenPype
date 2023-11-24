import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop

import hou


class ExtractRedshiftProxy(publish.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Redshift Proxy"
    families = ["redshiftproxy"]
    hosts = ["houdini"]
    targets = ["local", "remote"]

    def process(self, instance):
        if instance.data.get("farm"):
            self.log.debug("Should be processed on farm, skipping.")
            return
        ropnode = hou.node(instance.data.get("instance_node"))

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
        if "frameStartHandle" in instance.data and "frameEndHandle" in instance.data:  # noqa
            representation["frameStart"] = instance.data["frameStartHandle"]
            representation["frameEnd"] = instance.data["frameEndHandle"]

        instance.data["representations"].append(representation)
