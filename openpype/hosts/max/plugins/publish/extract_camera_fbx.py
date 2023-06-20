import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.pipeline import OptionalPyblishPluginMixin, publish


class ExtractCameraFbx(publish.Extractor, OptionalPyblishPluginMixin):
    """Extract Camera with FbxExporter."""

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Extract Fbx Camera"
    hosts = ["max"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        container = instance.data["instance_node"]

        self.log.info("Extracting Camera ...")
        stagingdir = self.staging_dir(instance)
        filename = "{name}.fbx".format(**instance.data)

        filepath = os.path.join(stagingdir, filename)
        self.log.info(f"Writing fbx file '{filename}' to '{filepath}'")

        rt.FBXExporterSetParam("Animation", True)
        rt.FBXExporterSetParam("Cameras", True)
        rt.FBXExporterSetParam("AxisConversionMethod", "Animation")
        rt.FBXExporterSetParam("UpAxis", "Y")
        rt.FBXExporterSetParam("Preserveinstances", True)

        with maintained_selection():
            # select and export
            node_list = instance.data["members"]
            rt.Select(node_list)
            rt.ExportFile(
                filepath,
                rt.Name("noPrompt"),
                selectedOnly=True,
                using=rt.FBXEXP,
            )

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "fbx",
            "ext": "fbx",
            "files": filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info(f"Extracted instance '{instance.name}' to: {filepath}")
