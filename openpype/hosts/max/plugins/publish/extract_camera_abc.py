import os
import pyblish.api
from openpype.pipeline import publish
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection,
    get_all_children
)


class ExtractAlembicCamera(publish.Extractor):
    """
    Extract Camera with AlembicExport
    """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Almebic Camera"
    hosts = ["max"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        start = float(instance.data.get("frameStartHandle", 1))
        end = float(instance.data.get("frameEndHandle", 1))

        container = instance.data["instance_node"]

        self.log.info("Extracting Camera ...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(stagingdir, filename)

        # We run the render
        self.log.info("Writing alembic '%s' to '%s'" % (filename,
                                                        stagingdir))

        export_cmd = (
            f"""
AlembicExport.ArchiveType = #ogawa
AlembicExport.CoordinateSystem = #maya
AlembicExport.StartFrame = {start}
AlembicExport.EndFrame = {end}
AlembicExport.CustomAttributes = true

exportFile @"{path}" #noPrompt selectedOnly:on using:AlembicExport

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
                                                          path))
