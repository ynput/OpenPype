import os

import pyblish.api
import colorbleed.api


class ExtractAlembic(colorbleed.api.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Pointcache (Alembic)"
    hosts = ["houdini"]
    families = ["colorbleed.pointcache"]

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.eval()` will make sure all tokens are resolved
        output = ropnode.parm("filename").eval()
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir

        file_name = os.path.basename(output)

        # We run the render
        self.log.info("Writing alembic '%s' to '%s'" % (file_name, staging_dir))
        ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(file_name)
