import os
import pyblish.api
from openpype.pipeline import publish, OptionalPyblishPluginMixin
from pymxs import runtime as rt
from openpype.hosts.max.api import maintained_selection
from openpype.hosts.max.api.lib import suspended_refresh
from openpype.pipeline.publish import KnownPublishError


class ExtractModelObj(publish.Extractor, OptionalPyblishPluginMixin):
    """
    Extract Geometry in OBJ Format
    """

    order = pyblish.api.ExtractorOrder - 0.05
    label = "Extract OBJ"
    hosts = ["max"]
    families = ["model"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        stagingdir = self.staging_dir(instance)
        filename = "{name}.obj".format(**instance.data)
        filepath = os.path.join(stagingdir, filename)

        with suspended_refresh():
            with maintained_selection():
                # select and export
                node_list = instance.data["members"]
                rt.Select(node_list)
                rt.exportFile(
                    filepath,
                    rt.name("noPrompt"),
                    selectedOnly=True,
                    using=rt.ObjExp,
                )
        if not os.path.exists(filepath):
            raise KnownPublishError(
                "File {} wasn't produced by 3ds max, please check the logs.")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "obj",
            "ext": "obj",
            "files": filename,
            "stagingDir": stagingdir,
        }

        instance.data["representations"].append(representation)
        self.log.info(
            "Extracted instance '%s' to: %s" % (instance.name, filepath)
        )
