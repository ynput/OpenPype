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


class ExtractModelUSD(publish.Extractor,
                      OptionalPyblishPluginMixin):
    """
    Extract Geometry in USDA Format
    """

    order = pyblish.api.ExtractorOrder - 0.05
    label = "Extract Geometry (USD)"
    hosts = ["max"]
    families = ["model"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        container = instance.data["instance_node"]

        self.log.info("Extracting Geometry ...")

        stagingdir = self.staging_dir(instance)
        asset_filename = "{name}.usda".format(**instance.data)
        asset_filepath = os.path.join(stagingdir,
                                      asset_filename)
        self.log.info("Writing USD '%s' to '%s'" % (asset_filepath,
                                                    stagingdir))

        log_filename = "{name}.txt".format(**instance.data)
        log_filepath = os.path.join(stagingdir,
                                    log_filename)
        self.log.info("Writing log '%s' to '%s'" % (log_filepath,
                                                    stagingdir))

        # get the nodes which need to be exported
        export_options = self.get_export_options(log_filepath)
        with maintained_selection():
            # select and export
            node_list = self.get_node_list(container)
            rt.USDExporter.ExportFile(asset_filepath,
                                      exportOptions=export_options,
                                      contentSource=rt.name("selected"),
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

        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          asset_filepath))

    def get_node_list(self, container):
        """
        Get the target nodes which are
        the children of the container
        """
        node_list = []

        container_node = rt.getNodeByName(container)
        target_node = container_node.Children
        rt.select(target_node)
        for sel in rt.selection:
            node_list.append(sel)

        return node_list

    def get_export_options(self, log_path):
        """Set Export Options for USD Exporter"""

        export_options = rt.USDExporter.createOptions()

        export_options.Meshes = True
        export_options.Shapes = False
        export_options.Lights = False
        export_options.Cameras = False
        export_options.Materials = False
        export_options.MeshFormat = rt.name('fromScene')
        export_options.FileFormat = rt.name('ascii')
        export_options.UpAxis = rt.name('y')
        export_options.LogLevel = rt.name('info')
        export_options.LogPath = log_path
        export_options.PreserveEdgeOrientation = True
        export_options.TimeMode = rt.name('current')

        rt.USDexporter.UIOptions = export_options

        return export_options
