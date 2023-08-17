import os
import pyblish.api
from openpype.pipeline import publish, OptionalPyblishPluginMixin
from pymxs import runtime as rt
from openpype.hosts.max.api import maintained_selection


class ExtractModel(publish.Extractor, OptionalPyblishPluginMixin):
    """
    Extract Geometry in Alembic Format
    """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Geometry (Alembic)"
    hosts = ["max"]
    families = ["model"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        container = instance.data["instance_node"]

        self.log.info("Extracting Geometry ...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        filepath = os.path.join(stagingdir, filename)

        # We run the render
        self.log.info("Writing alembic '%s' to '%s'" % (filename, stagingdir))

        rt.AlembicExport.ArchiveType = rt.name("ogawa")
        rt.AlembicExport.CoordinateSystem = rt.name("maya")
        rt.AlembicExport.CustomAttributes = True
        rt.AlembicExport.UVs = True
        rt.AlembicExport.VertexColors = True
        rt.AlembicExport.PreserveInstances = True

        with maintained_selection():
            # select and export
            node_list = instance.data["members"]
            rt.Select(node_list)
            rt.exportFile(
                filepath,
                rt.name("noPrompt"),
                selectedOnly=True,
                using=rt.AlembicExport,
            )

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "abc",
            "ext": "abc",
            "files": filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info(
            "Extracted instance '%s' to: %s" % (instance.name, filepath)
        )
