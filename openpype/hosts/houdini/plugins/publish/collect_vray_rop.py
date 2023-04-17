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


class CollectVrayROPRenderProducts(pyblish.api.InstancePlugin):
    """Collect Vray Render Products

    Collects the instance.data["files"] for the render products.

    Provides:
        instance    -> files

    """

    label = "VRay ROP Render Products"
    order = pyblish.api.CollectorOrder + 0.4
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

        beauty_product = self.get_beauty_render_product(default_prefix)
        render_products.append(beauty_product)
        files_by_aov = {
            "RGB Color": self.generate_expected_files(instance,
                                                      beauty_product)}

        if instance.data.get("RenderElement", True):
            render_element = self.get_render_element_name(rop, default_prefix)
            if render_element:
                for aov, renderpass in render_element.items():
                    render_products.append(renderpass)
                    files_by_aov[aov] = self.generate_expected_files(instance, renderpass)          # noqa

        for product in render_products:
            self.log.debug("Found render product: %s" % product)
            filenames = list(render_products)
            instance.data["files"] = filenames
        self.log.debug("files:{}".format(render_products))

        # For now by default do NOT try to publish the rendered output
        instance.data["publishJobState"] = "Suspended"
        instance.data["attachTo"] = []      # stub required data

        if "expectedFiles" not in instance.data:
            instance.data["expectedFiles"] = list()
        instance.data["expectedFiles"].append(files_by_aov)
        self.log.debug("expectedFiles:{}".format(files_by_aov))

    def get_beauty_render_product(self, prefix, suffix="<reName>"):
        """Return the beauty output filename if render element enabled
        """
        aov_parm = ".{}".format(suffix)
        beauty_product = None
        if aov_parm in prefix:
            beauty_product = prefix.replace(aov_parm, "")
        else:
            beauty_product = prefix

        return beauty_product

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
