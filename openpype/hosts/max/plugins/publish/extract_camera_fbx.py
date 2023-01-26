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


class ExtractCameraFbx(publish.Extractor,
                       OptionalPyblishPluginMixin):
    """
    Extract Camera with FbxExporter
    """

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
        self.log.info("Writing fbx file '%s' to '%s'" % (filename,
                                                         filepath))

        # Need to export:
        # Animation = True
        # Cameras = True
        # AxisConversionMethod
        fbx_export_cmd = (
            f"""

FBXExporterSetParam "Animation" true
FBXExporterSetParam "Cameras" true
FBXExporterSetParam "AxisConversionMethod" "Animation"
FbxExporterSetParam "UpAxis" "Y"
FbxExporterSetParam "Preserveinstances" true

exportFile @"{filepath}" #noPrompt selectedOnly:true using:FBXEXP

            """)

        self.log.debug(f"Executing command: {fbx_export_cmd}")

        with maintained_selection():
            # select and export
            rt.select(get_all_children(rt.getNodeByName(container)))
            rt.execute(fbx_export_cmd)

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          filepath))
