import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop

import hou


class ExtractRedshiftProxy(publish.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract FilmBox FBX"
    families = ["filmboxfbx"]
    hosts = ["houdini"]

    # overrides InstancePlugin.process()
    def process(self, instance):

        ropnode = hou.node(instance.data.get("instance_node"))

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        output = ropnode.evalParm("sopoutput")
        staging_dir = os.path.normpath(os.path.dirname(output))
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        self.log.info("Writing FBX '%s' to '%s'" % (file_name,
                                                    staging_dir))

        render_rop(ropnode)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "fbx",
            "ext": "fbx",
            "files": file_name,
            "stagingDir": staging_dir,
        }

        # A single frame may also be rendered without start/end frame.
        if "frameStart" in instance.data and "frameEnd" in instance.data:
            representation["frameStart"] = instance.data["frameStart"]
            representation["frameEnd"] = instance.data["frameEnd"]

        instance.data["representations"].append(representation)
