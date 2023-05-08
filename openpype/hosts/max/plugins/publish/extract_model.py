import os
import pyblish.api
from openpype.pipeline import (
    publish,
    OptionalPyblishPluginMixin
)
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection,
    get_all_children
)


class ExtractModel(publish.Extractor,
                   OptionalPyblishPluginMixin):
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
        self.log.info("Writing alembic '%s' to '%s'" % (filename,
                                                        stagingdir))

        export_cmd = (
            f"""
AlembicExport.ArchiveType = #ogawa
AlembicExport.CoordinateSystem = #maya
AlembicExport.CustomAttributes = true
AlembicExport.UVs = true
AlembicExport.VertexColors = true
AlembicExport.PreserveInstances = true

exportFile @"{filepath}" #noPrompt selectedOnly:on using:AlembicExport

            """)

        self.log.debug(f"Executing command: {export_cmd}")

        with maintained_selection():
            # select and export
            rt.select(get_all_children(rt.getNodeByName(container)))
            rt.execute(export_cmd)

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          filepath))
