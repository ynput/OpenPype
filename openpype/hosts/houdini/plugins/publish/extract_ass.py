import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop

import hou


class ExtractAss(publish.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Ass"
    families = ["ass"]
    hosts = ["houdini"]
    targets = ["local", "remote"]

    def process(self, instance):
        if instance.data.get("farm"):
            self.log.debug("Should be processed on farm, skipping.")
            return
        ropnode = hou.node(instance.data["instance_node"])

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        output = ropnode.evalParm("ar_ass_file")
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        # We run the render
        self.log.info("Writing ASS '%s' to '%s'" % (file_name, staging_dir))

        render_rop(ropnode)

        # Unfortunately user interrupting the extraction does not raise an
        # error and thus still continues to the integrator. To capture that
        # we make sure all files exist
        files = instance.data["frames"]
        missing = []
        for file_name in files:
            full_path = os.path.normpath(os.path.join(staging_dir, file_name))
            if not os.path.exists(full_path):
                missing.append(full_path)

        if missing:
            raise RuntimeError("Failed to complete Arnold ass extraction. "
                               "Missing output files: {}".format(missing))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        # Allow ass.gz extension as well
        ext = "ass.gz" if file_name.endswith(".ass.gz") else "ass"

        representation = {
            'name': 'ass',
            'ext': ext,
            "files": files,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"],
        }
        instance.data["representations"].append(representation)
