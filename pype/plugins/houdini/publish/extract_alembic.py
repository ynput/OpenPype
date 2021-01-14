import os

import pyblish.api
import pype.api


class ExtractAlembic(pype.api.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Alembic"
    hosts = ["houdini"]
    families = ["pointcache", "camera"]

    def process(self, instance):

        import hou

        ropnode = instance[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        staging_dir = os.path.dirname(output)
        # instance.data["stagingDir"] = staging_dir

        file_name = os.path.basename(output)

        # We run the render
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        staging_dir))
        try:
            ropnode.render()
        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': file_name,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)
