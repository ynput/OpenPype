import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.pipeline import OptionalPyblishPluginMixin, publish


class ExtractModelUSD(publish.Extractor,
                      OptionalPyblishPluginMixin):
    """Extract Geometry in USDA Format."""

    order = pyblish.api.ExtractorOrder - 0.05
    label = "Extract Geometry (USD)"
    hosts = ["max"]
    families = ["model"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        self.log.info("Extracting Geometry ...")

        stagingdir = self.staging_dir(instance)
        asset_filename = "{name}.usda".format(**instance.data)
        asset_filepath = os.path.join(stagingdir,
                                      asset_filename)
        self.log.info(f"Writing USD '{asset_filepath}' to '{stagingdir}'")

        log_filename = "{name}.txt".format(**instance.data)
        log_filepath = os.path.join(stagingdir,
                                    log_filename)
        self.log.info(f"Writing log '{log_filepath}' to '{stagingdir}'")

        # get the nodes which need to be exported
        export_options = self.get_export_options(log_filepath)
        with maintained_selection():
            # select and export
            node_list = instance.data["members"]
            rt.Select(node_list)
            rt.USDExporter.ExportFile(asset_filepath,
                                      exportOptions=export_options,
                                      contentSource=rt.Name("selected"),
                                      nodeList=node_list)

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'usda',
            'ext': 'usda',
            'files': asset_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        log_representation = {
            'name': 'txt',
            'ext': 'txt',
            'files': log_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(log_representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {asset_filepath}")

    @staticmethod
    def get_export_options(log_path):
        """Set Export Options for USD Exporter"""

        export_options = rt.USDExporter.createOptions()

        export_options.Meshes = True
        export_options.Shapes = False
        export_options.Lights = False
        export_options.Cameras = False
        export_options.Materials = False
        export_options.MeshFormat = rt.Name('fromScene')
        export_options.FileFormat = rt.Name('ascii')
        export_options.UpAxis = rt.Name('y')
        export_options.LogLevel = rt.Name('info')
        export_options.LogPath = log_path
        export_options.PreserveEdgeOrientation = True
        export_options.TimeMode = rt.Name('current')

        rt.USDexporter.UIOptions = export_options

        return export_options
