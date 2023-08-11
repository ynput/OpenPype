import os
import re

import hou
import pyblish.api

from openpype.pipeline import expected_files
from openpype.hosts.houdini.api import colorspace
from openpype.hosts.houdini.api.lib import (
    evalParmNoFrame, get_color_management_preferences)


class CollectArnoldROPRenderProducts(pyblish.api.InstancePlugin):
    """Collect Arnold ROP Render Products

    Collects the instance.data["files"] for the render products.

    Provides:
        instance    -> files

    """

    label = "Arnold ROP Render Products"
    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]
    families = ["arnold_rop"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: %s" % chunk_size)

        default_prefix = evalParmNoFrame(rop, "ar_picture")
        render_products = []

        # Default beauty AOV
        beauty_product = self.get_render_product_name(prefix=default_prefix,
                                                      suffix=None)
        render_products.append(beauty_product)

        files_by_aov = {
            "": expected_files.generate_expected_files(
                frame_start, frame_end, beauty_product)
        }

        num_aovs = rop.evalParm("ar_aovs")
        for index in range(1, num_aovs + 1):
            # Skip disabled AOVs
            if not rop.evalParm("ar_enable_aov{}".format(index)):
                continue

            if rop.evalParm("ar_aov_exr_enable_layer_name{}".format(index)):
                label = rop.evalParm("ar_aov_exr_layer_name{}".format(index))
            else:
                label = evalParmNoFrame(rop, "ar_aov_label{}".format(index))

            aov_product = self.get_render_product_name(default_prefix,
                                                       suffix=label)
            render_products.append(aov_product)
            files_by_aov[label] = expected_files.generate_expected_files(
                frame_start, frame_end, aov_product)

        for product in render_products:
            self.log.debug("Found render product: {}".format(product))

        instance.data["files"] = list(render_products)
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
        """Return the output filename using the AOV prefix and suffix"""

        # When AOV is explicitly defined in prefix we just swap it out
        # directly with the AOV suffix to embed it.
        # Note: ${AOV} seems to be evaluated in the parameter as %AOV%
        if "%AOV%" in prefix:
            # It seems that when some special separator characters are present
            # before the %AOV% token that Redshift will secretly remove it if
            # there is no suffix for the current product, for example:
            # foo_%AOV% -> foo.exr
            pattern = "%AOV%" if suffix else "[._-]?%AOV%"
            product_name = re.sub(pattern,
                                  suffix,
                                  prefix,
                                  flags=re.IGNORECASE)
        else:
            if suffix:
                # Add ".{suffix}" before the extension
                prefix_base, ext = os.path.splitext(prefix)
                product_name = prefix_base + "." + suffix + ext
            else:
                product_name = prefix

        return product_name
