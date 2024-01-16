import os
import pyblish.api
from openpype.pipeline import publish, OptionalPyblishPluginMixin
from pymxs import runtime as rt
from openpype.hosts.max.api import maintained_selection
from openpype.hosts.max.api.lib import convert_unit_scale


class ExtractModelFbx(publish.Extractor, OptionalPyblishPluginMixin):
    """
    Extract Geometry in FBX Format
    """

    order = pyblish.api.ExtractorOrder - 0.05
    label = "Extract FBX"
    hosts = ["max"]
    families = ["model"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        stagingdir = self.staging_dir(instance)
        filename = "{name}.fbx".format(**instance.data)
        filepath = os.path.join(stagingdir, filename)
        self._set_fbx_attributes()

        with maintained_selection():
            # select and export
            node_list = instance.data["members"]
            rt.Select(node_list)
            rt.exportFile(
                filepath,
                rt.name("noPrompt"),
                selectedOnly=True,
                using=rt.FBXEXP,
            )

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "fbx",
            "ext": "fbx",
            "files": filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info(
            "Extracted instance '%s' to: %s" % (instance.name, filepath)
        )

    def _set_fbx_attributes(self):
        unit_scale = convert_unit_scale()
        rt.FBXExporterSetParam("Animation", False)
        rt.FBXExporterSetParam("Cameras", False)
        rt.FBXExporterSetParam("Lights", False)
        rt.FBXExporterSetParam("PointCache", False)
        rt.FBXExporterSetParam("AxisConversionMethod", "Animation")
        rt.FBXExporterSetParam("UpAxis", "Y")
        rt.FBXExporterSetParam("Preserveinstances", True)
        if unit_scale:
            rt.FBXExporterSetParam("ConvertUnit", unit_scale)


class ExtractCameraFbx(ExtractModelFbx):
    """Extract Camera with FbxExporter."""

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Extract Fbx Camera"
    families = ["camera"]
    optional = True

    def _set_fbx_attributes(self):
        unit_scale = convert_unit_scale()
        rt.FBXExporterSetParam("Animation", True)
        rt.FBXExporterSetParam("Cameras", True)
        rt.FBXExporterSetParam("AxisConversionMethod", "Animation")
        rt.FBXExporterSetParam("UpAxis", "Y")
        rt.FBXExporterSetParam("Preserveinstances", True)
        if unit_scale:
            rt.FBXExporterSetParam("ConvertUnit", unit_scale)
