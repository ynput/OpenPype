import os

import pyblish.api
import pype.api


class ExtractVDBCache(pype.api.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    families = ["vdbcache"]
    hosts = ["houdini"]

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        sop_output = ropnode.evalParm("sopoutput")
        staging_dir = os.path.normpath(os.path.dirname(sop_output))
        instance.data["stagingDir"] = staging_dir

        if instance.data.get("executeBackground", True):
            self.log.info("Creating background task..")
            ropnode.parm("executebackground").pressButton()
            self.log.info("Finished")
        else:
            ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        output = instance.data["frames"]

        instance.data["files"].append(output)
