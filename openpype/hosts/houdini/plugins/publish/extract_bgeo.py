import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop
from openpype.hosts.houdini.api import lib

import hou


class ExtractBGEO(publish.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract BGEO"
    hosts = ["houdini"]
    families = ["bgeo"]

    def process(self, instance):
        if instance.data.get("farm"):
            self.log.debug("Should be processed on farm, skipping.")
            return
        ropnode = hou.node(instance.data["instance_node"])

        # Get the filename from the filename parameter
        output = ropnode.evalParm("sopoutput")
        staging_dir, file_name = os.path.split(output)
        instance.data["stagingDir"] = staging_dir

        # We run the render
        self.log.info("Writing bgeo files '{}' to '{}'.".format(
            file_name, staging_dir))

        # write files
        render_rop(ropnode)

        output = instance.data["frames"]

        _, ext = lib.splitext(
            output[0], allowed_multidot_extensions=[
                ".ass.gz", ".bgeo.sc", ".bgeo.gz",
                ".bgeo.lzma", ".bgeo.bz2"])

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "bgeo",
            "ext": ext.lstrip("."),
            "files": output,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"]
        }
        instance.data["representations"].append(representation)
