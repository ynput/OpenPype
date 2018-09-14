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
        file_name = os.path.basename(ropnode.parm("filename").eval())

        # We run the render
        ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(file_name)
