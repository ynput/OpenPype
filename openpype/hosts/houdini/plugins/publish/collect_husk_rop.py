import re
import os

import hou
import pyblish.api
import math

from openpype.hosts.houdini.api.lib import (
    evalParmNoFrame,
    get_color_management_preferences
)
from openpype.hosts.houdini.api import (
    colorspace
)


class CollectHuskROPProducts(pyblish.api.InstancePlugin):
    """Collect Husk Products

    Collects the instance.data["files"] for the render products.

    Provides:
        instance    -> files

    """

    label = "Husk ROP Products"
    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]
    families = ["husk"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))
        
        self.log.debug("Instance data: %s" % instance.data)

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: %s" % chunk_size)

            default_prefix = evalParmNoFrame(rop, "outputimage")
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

        # Generate the commandline
        instance.data["huskCommandline"] = self._generate_command(rop, instance)

        # submit to deadline for test purposes only
        self.submit(rop, instance)

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
        start = instance.data["frameStart"]
        end = instance.data["frameEnd"]
        for i in range(int(start), (int(end) + 1)):
            expected_files.append(
                os.path.join(dir, (file % i)).replace("\\", "/"))

        return expected_files

    def _generate_command(self, node, instance):
        chunkSize = node.parm('chunkSize').eval()
        renderer = node.parm('renderer')
        self.log.debug("renderer: %s" % renderer)
        verbosity = node.parm('verbosity').eval()

        # hardcoded usdfile --  we must replace but how?
        usdfile = "the_path_for_usdfile.usd"
        self.log.debug("usdfile: %s" % usdfile)

        start = instance.data["frameStart"]
        end = instance.data["frameEnd"]
        inc = instance.data["byFrameStep"]

        output = node.parm('outputimage').eval()
        output = output[:-8] + '%04d.exr'

        outputDir = output.split('/')[:-1]
        outputDir = '/'.join(outputDir)

        if not os.path.exists(outputDir):
            os.makedirs(outputDir)

        self.log.debug("output: %s" % output)

        rendererLabel = renderer.eval()
        self.log.debug("rendererLabel: %s" % rendererLabel)

        framesToRender = float(end - start) / inc
        if framesToRender < chunkSize:
            chunkSize = math.ceil(framesToRender)
        self.log.debug("chunkSize: %s" % chunkSize)

        if os.name == 'nt':
            husk_bin = 'husk.exe'
        else:
            hfs = hou.getenv('HFS')
            if hfs:
                husk_bin = hfs + '/bin/husk'
            else:
                print("$HFS variable is not set. It's required for running Husk command.")
                raise ValueError('HFS missing')

        command = []
        command.append(husk_bin)
        command.append('-R %s' % rendererLabel)
        command.append('-f <STARTFRAME>')
        command.append('-n %s' % chunkSize)
        command.append('-i %s' % inc)
        command.append('-Va%s' % verbosity)
        command.append('-o %s' % output)
        command.append('--make-output-path')
        command.append('--exrmode 0')
        command.append('--snapshot 60')
        command.append('--snapshot-suffix ""')
        command.append(usdfile)
        command.append('-e <ENDFRAME>')
        command = ' '.join(command)

        self.log.debug("command: %s" % command)

        return command
