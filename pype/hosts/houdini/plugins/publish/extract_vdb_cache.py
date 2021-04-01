import os

import pyblish.api
import openpype.api


class ExtractVDBCache(openpype.api.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    families = ["vdbcache"]
    hosts = ["houdini"]

    def process(self, instance):

        import hou

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        sop_output = ropnode.evalParm("sopoutput")
        staging_dir = os.path.normpath(os.path.dirname(sop_output))
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(sop_output)

        self.log.info("Writing VDB '%s' to '%s'" % (file_name, staging_dir))
        try:
            ropnode.render()
        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))

        output = instance.data["frames"]

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'mov',
            'ext': 'mov',
            'files': output,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)
