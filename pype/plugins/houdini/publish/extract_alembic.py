import os

import pyblish.api
import pype.api


class ExtractAlembic(pype.api.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Alembic"
    hosts = ["houdini"]
    families = ["pointcache", "camera"]

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir

        file_name = os.path.basename(output)

        # We run the render
        self.log.info("Writing alembic '%s' to '%s'" % (file_name, staging_dir))
        ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(file_name)
