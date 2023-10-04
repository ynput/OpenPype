import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.pipeline import OptionalPyblishPluginMixin, publish


class ExtractCameraAlembic(publish.Extractor, OptionalPyblishPluginMixin):
    """Extract Camera with AlembicExport."""

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Alembic Camera"
    hosts = ["max"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        start = float(instance.data.get("frameStartHandle", 1))
        end = float(instance.data.get("frameEndHandle", 1))

        self.log.info("Extracting Camera ...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(stagingdir, filename)

        # We run the render
        self.log.info(f"Writing alembic '{filename}' to '{stagingdir}'")

        rt.AlembicExport.ArchiveType = rt.Name("ogawa")
        rt.AlembicExport.CoordinateSystem = rt.Name("maya")
        rt.AlembicExport.StartFrame = start
        rt.AlembicExport.EndFrame = end
        rt.AlembicExport.CustomAttributes = True

        with maintained_selection():
            # select and export
            node_list = instance.data["members"]
            rt.Select(node_list)
            rt.ExportFile(
                path,
                rt.Name("noPrompt"),
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
            "frameStart": start,
            "frameEnd": end,
        }
        instance.data["representations"].append(representation)
        self.log.info(f"Extracted instance '{instance.name}' to: {path}")
