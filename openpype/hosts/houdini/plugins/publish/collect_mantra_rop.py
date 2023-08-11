import os

import hou
import pyblish.api

from openpype.pipeline import expected_files
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
    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]
    families = ["mantra_rop"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if not chunk_size_parm:
            return

        chunk_size = int(chunk_size_parm.eval())
        instance.data["chunkSize"] = chunk_size
        self.log.debug("Chunk Size: {}".format(chunk_size))

        default_prefix = evalParmNoFrame(rop, "vm_picture")
        render_products = []

        # Default beauty AOV
        beauty_product = self.get_render_product_name(
            prefix=default_prefix, suffix=None
        )
        render_products.append(beauty_product)

        files_by_aov = {
            "beauty": expected_files.generate_expected_filepaths(
                frame_start, frame_end, beauty_product)
        }

        # get the number of AOVs
        aov_numbers = rop.evalParm("vm_numaux")
        if aov_numbers < 0:
            return

        # get the filenames of the AOVs
        for index in range(1, aov_numbers + 1):
            var_ = rop.evalParm("vm_variable_plane{:>1}".format(index))

            # skip empty variables
            if not var_:
                continue

            aov_name = "vm_filename_plane{:>1}".format(index)
            aov_boolean = "vm_usefile_plane{:>1}".format(index)
            aov_enabled = rop.evalParm(aov_boolean)
            has_aov_path = rop.evalParm(aov_name)

            # skip disabled AOVs
            if not (has_aov_path and aov_enabled == 1):
                continue

            aov_prefix = evalParmNoFrame(rop, aov_name)
            aov_product = self.get_render_product_name(
                prefix=aov_prefix, suffix=None
            )
            render_products.append(aov_product)

            files_by_aov[var_] = expected_files.generate_expected_filepaths(
                frame_start, frame_end, aov_product)

        for product in render_products:
            self.log.debug("Found render product: {}".format(product))

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
