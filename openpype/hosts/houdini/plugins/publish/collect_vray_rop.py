import re
import os

import hou
import pyblish.api

from openpype.hosts.houdini.api.lib import (
    evalParmNoFrame,
    get_color_management_preferences
)
from openpype.hosts.houdini.api import (
    colorspace
)


class CollectVrayROPRenderProducts(pyblish.api.InstancePlugin):
    """Collect Vray Render Products

    Collects the instance.data["files"] for the render products.

    Provides:
        instance    -> files

    """

    label = "VRay ROP Render Products"
    # This specific order value is used so that
    # this plugin runs after CollectFrames
    order = pyblish.api.CollectorOrder + 0.11
    hosts = ["houdini"]
    families = ["vray_rop"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: %s" % chunk_size)

        default_prefix = evalParmNoFrame(rop, "SettingsOutput_img_file_path")
        render_products = []
        # TODO: add render elements if render element

        # Store whether we are splitting the render job in an export + render
        split_render = rop.parm("render_export_mode").eval() == "2"
        instance.data["splitRender"] = split_render
        export_prefix = None
        export_products = []
        if split_render:
            export_prefix = evalParmNoFrame(
                rop, "render_export_filepath", pad_character="0"
            )
            beauty_export_product = self.get_render_product_name(
                prefix=export_prefix,
                suffix=None)
            export_products.append(beauty_export_product)
            self.log.debug(
                "Found export product: {}".format(beauty_export_product)
            )
            instance.data["ifdFile"] = beauty_export_product
            instance.data["exportFiles"] = list(export_products)

        beauty_product = self.get_render_product_name(default_prefix)
        render_products.append(beauty_product)
        files_by_aov = {
            "": self.generate_expected_files(instance,
                                                      beauty_product)}

        if instance.data.get("RenderElement", True):
            render_element = self.get_render_element_name(rop, default_prefix)
            if render_element:
                for aov, renderpass in render_element.items():
                    render_products.append(renderpass)
                    files_by_aov[aov] = self.generate_expected_files(
                        instance, renderpass)


        for product in render_products:
            self.log.debug("Found render product: %s" % product)
        filenames = list(render_products)
        instance.data["files"] = filenames
        instance.data["renderProducts"] = colorspace.ARenderProduct()

        # For now by default do NOT try to publish the rendered output
        instance.data["publishJobState"] = "Suspended"
        instance.data["attachTo"] = []      # stub required data

        if "expectedFiles" not in instance.data:
            instance.data["expectedFiles"] = list()
        instance.data["expectedFiles"].append(files_by_aov)
        self.log.debug("expectedFiles:{}".format(files_by_aov))

        # update the colorspace data
        colorspace_data = get_color_management_preferences()
        instance.data["colorspaceConfig"] = colorspace_data["config"]
        instance.data["colorspaceDisplay"] = colorspace_data["display"]
        instance.data["colorspaceView"] = colorspace_data["view"]

    def get_render_product_name(self, prefix, suffix="<reName>"):
        """Return the beauty output filename if render element enabled
        """
        # Remove aov suffix from the product: `prefix.aov_suffix` -> `prefix`
        aov_parm = ".{}".format(suffix)
        return prefix.replace(aov_parm, "")

    def get_render_element_name(self, node, prefix, suffix="<reName>"):
        """Return the output filename using the AOV prefix and suffix
        """
        render_element_dict = {}
        # need a rewrite
        re_path = node.evalParm("render_network_render_channels")
        if re_path:
            node_children = hou.node(re_path).children()
            for element in node_children:
                if element.shaderName() != "vray:SettingsRenderChannels":
                    aov = str(element)
                    render_product = prefix.replace(suffix, aov)
                    render_element_dict[aov] = render_product
        return render_element_dict

    def generate_expected_files(self, instance, path):
        """Create expected files in instance data"""

        dir = os.path.dirname(path)
        file = os.path.basename(path)

        if "#" in file:
            def replace(match):
                return "%0{}d".format(len(match.group()))

            file = re.sub("#+", replace, file)

        if "%" not in file:
            return path

        expected_files = []
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        for i in range(int(start), (int(end) + 1)):
            expected_files.append(
                os.path.join(dir, (file % i)).replace("\\", "/"))

        return expected_files
