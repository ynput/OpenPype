import os
import re

import hou
import pyblish.api

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
    # This specific order value is used so that
    # this plugin runs after CollectFrames
    order = pyblish.api.CollectorOrder + 0.11
    hosts = ["houdini"]
    families = ["arnold_rop"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: %s" % chunk_size)

        default_prefix = evalParmNoFrame(rop, "ar_picture")
        render_products = []

        # Store whether we are splitting the render job (export + render)
        split_render = bool(rop.parm("ar_ass_export_enable").eval())
        instance.data["splitRender"] = split_render
        export_prefix = None
        export_products = []
        if split_render:
            export_prefix = evalParmNoFrame(
                rop, "ar_ass_file", pad_character="0"
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
        beauty_product = self.get_render_product_name(prefix=default_prefix,
                                                      suffix=None)
        render_products.append(beauty_product)

        files_by_aov = {
            "": self.generate_expected_files(instance, beauty_product)
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
            files_by_aov[label] = self.generate_expected_files(instance,
                                                               aov_product)

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
