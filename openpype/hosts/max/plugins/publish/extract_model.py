import os
import pyblish.api
from openpype.pipeline import (
    publish,
    OptionalPyblishPluginMixin
)
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection
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

        self.log.info("Extracting Geometry ...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        filepath = os.path.join(stagingdir, filename)

        # We run the render
        self.log.info(f"Writing alembic '{filename}' to '{stagingdir}'")

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
            rt.Select(instance.data["members"])
            rt.Execute(export_cmd)

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
        self.log.info(f"Extracted instance '{instance.name}' to: {filepath}")
