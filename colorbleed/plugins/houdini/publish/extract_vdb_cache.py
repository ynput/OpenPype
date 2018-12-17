import os

import pyblish.api
import colorbleed.api


class ExtractVDBCache(colorbleed.api.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    families = ["colorbleed.vdbcache"]
    hosts = ["houdini"]

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        sop_output = ropnode.evalParm("sopoutput")
        staging_dir = os.path.normpath(os.path.dirname(sop_output))
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(sop_output)

        self.log.info("Writing VDB '%s' to '%s'" % (file_name, staging_dir))
        ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        output = instance.data["frames"]

        instance.data["files"].append(output)
