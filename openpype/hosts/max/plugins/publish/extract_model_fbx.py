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


class ExtractModelFbx(publish.Extractor,
                      OptionalPyblishPluginMixin):
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

        container = instance.data["instance_node"]

        self.log.info("Extracting Geometry ...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.fbx".format(**instance.data)
        filepath = os.path.join(stagingdir,
                                filename)
        self.log.info("Writing FBX '%s' to '%s'" % (filepath,
                                                    stagingdir))

        export_fbx_cmd = (
            f"""
FBXExporterSetParam "Animation" false
FBXExporterSetParam "Cameras" false
FBXExporterSetParam "Lights" false
FBXExporterSetParam "PointCache" false
FBXExporterSetParam "AxisConversionMethod" "Animation"
FbxExporterSetParam "UpAxis" "Y"
FbxExporterSetParam "Preserveinstances" true

exportFile @"{filepath}" #noPrompt selectedOnly:true using:FBXEXP

            """)

        self.log.debug(f"Executing command: {export_fbx_cmd}")

        with maintained_selection():
            # select and export
            rt.select(get_all_children(rt.getNodeByName(container)))
            rt.execute(export_fbx_cmd)

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
