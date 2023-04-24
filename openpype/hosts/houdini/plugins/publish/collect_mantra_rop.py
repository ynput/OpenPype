import re
import os

import hou
import pyblish.api


def get_top_referenced_parm(parm):

    processed = set()  # disallow infinite loop
    while True:
        if parm.path() in processed:
            raise RuntimeError("Parameter references result in cycle.")

        processed.add(parm.path())

        ref = parm.getReferencedParm()
        if ref.path() == parm.path():
            # It returns itself when it doesn't reference
            # another parameter
            return ref
        else:
            parm = ref


def evalParmNoFrame(node, parm, pad_character="#"):

    parameter = node.parm(parm)
    assert parameter, "Parameter does not exist: %s.%s" % (node, parm)

    # If the parameter has a parameter reference, then get that
    # parameter instead as otherwise `unexpandedString()` fails.
    parameter = get_top_referenced_parm(parameter)

    # Substitute out the frame numbering with padded characters
    try:
        raw = parameter.unexpandedString()
    except hou.Error as exc:
        print("Failed: %s" % parameter)
        raise RuntimeError(exc)

    def replace(match):
        padding = 1
        n = match.group(2)
        if n and int(n):
            padding = int(n)
        return pad_character * padding

    expression = re.sub(r"(\$F([0-9]*))", replace, raw)

    with hou.ScriptEvalContext(parameter):
        return hou.expandStringAtFrame(expression, 0)


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

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: %s" % chunk_size)

            default_prefix = evalParmNoFrame(rop, "vm_picture")
            render_products = []

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

        # For now by default do NOT try to publish the rendered output
        instance.data["publishJobState"] = "Suspended"
        instance.data["attachTo"] = []      # stub required data

        if "expectedFiles" not in instance.data:
            instance.data["expectedFiles"] = list()
        instance.data["expectedFiles"].append(files_by_aov)

    def get_render_product_name(self, prefix, suffix):
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
            pparts = file.split("#")
            padding = "%0{}d".format(len(pparts) - 1)
            file = pparts[0] + padding + pparts[-1]

        if "%" not in file:
            return path

        expected_files = []
        start = instance.data["frameStart"]
        end = instance.data["frameEnd"]
        for i in range(int(start), (int(end) + 1)):
            expected_files.append(
                os.path.join(dir, (file % i)).replace("\\", "/"))

        return expected_files
