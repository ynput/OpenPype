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


class CollectMantraROPRenderProducts(pyblish.api.InstancePlugin):
    """Collect Mantra Render Products

    Collects the instance.data["files"] for the render products.

    Provides:
        instance    -> files

    """

    label = "Mantra ROP Render Products"
    # This specific order value is used so that
    # this plugin runs after CollectFrames
    order = pyblish.api.CollectorOrder + 0.11
    hosts = ["houdini"]
    families = ["mantra_rop"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: %s" % chunk_size)

            default_prefix = evalParmNoFrame(rop, "vm_picture")
            render_products = []

            # Store whether we are splitting the render job (export + render)
            split_render = bool(rop.parm("soho_outputmode").eval())
            instance.data["splitRender"] = split_render
            export_prefix = None
            export_products = []
            if split_render:
                export_prefix = evalParmNoFrame(
                    rop, "soho_diskfile", pad_character="0"
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

            # Default beauty AOV
            beauty_product = self.get_render_product_name(
                prefix=default_prefix, suffix=None
            )
            render_products.append(beauty_product)

            files_by_aov = {
                "beauty": self.generate_expected_files(instance,
                                                       beauty_product)
            }

            aov_numbers = rop.evalParm("vm_numaux")
            if aov_numbers > 0:
                # get the filenames of the AOVs
                for i in range(1, aov_numbers + 1):
                    var = rop.evalParm("vm_variable_plane%d" % i)
                    if var:
                        aov_name = "vm_filename_plane%d" % i
                        aov_boolean = "vm_usefile_plane%d" % i
                        aov_enabled = rop.evalParm(aov_boolean)
                        has_aov_path = rop.evalParm(aov_name)
                        if has_aov_path and aov_enabled == 1:
                            aov_prefix = evalParmNoFrame(rop, aov_name)
                            aov_product = self.get_render_product_name(
                                prefix=aov_prefix, suffix=None
                            )
                            render_products.append(aov_product)

                            files_by_aov[var] = self.generate_expected_files(instance, aov_product)     # noqa

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

        # update the colorspace data
        colorspace_data = get_color_management_preferences()
        instance.data["colorspaceConfig"] = colorspace_data["config"]
        instance.data["colorspaceDisplay"] = colorspace_data["display"]
        instance.data["colorspaceView"] = colorspace_data["view"]

    def get_render_product_name(self, prefix, suffix):
        product_name = prefix
        if suffix:
            # Add ".{suffix}" before the extension
            prefix_base, ext = os.path.splitext(prefix)
            product_name = prefix_base + "." + suffix + ext

        return product_name

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
