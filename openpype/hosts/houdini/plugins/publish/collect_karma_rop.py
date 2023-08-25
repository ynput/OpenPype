import re
import os

import hou
import pyblish.api

from openpype.pipeline import file_collection
from openpype.hosts.houdini.api.lib import (
    evalParmNoFrame,
    get_color_management_preferences
)
from openpype.hosts.houdini.api import (
    colorspace
)


class CollectKarmaROPRenderProducts(pyblish.api.InstancePlugin):
    """Collect Karma Render Products

    Collects the instance.data["files"] for the multipart render product.

    Provides:
        instance    -> files

    """

    label = "Karma ROP Render Products"
    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]
    families = ["karma_rop"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: {}".format(chunk_size))

        default_prefix = evalParmNoFrame(rop, "picture")
        render_products = []

        # Default beauty AOV
        beauty_product = self.get_render_product_name(
            prefix=default_prefix, suffix=None
        )
        render_products.append(beauty_product)

        files_by_aov = {
            "beauty": file_collection.generate_expected_filepaths(
                frame_start, frame_end, beauty_product)
        }

        filenames = list(render_products)
        instance.data["files"] = filenames
        instance.data["renderProducts"] = colorspace.ARenderProduct()

        for product in render_products:
            self.log.debug("Found render product: %s" % product)

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
            product_name = "{}.{}{}".format(prefix_base, suffix, ext)

        return product_name
