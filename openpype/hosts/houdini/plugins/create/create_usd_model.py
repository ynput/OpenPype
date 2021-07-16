import re
from openpype.hosts.houdini.api import plugin
import hou


class CreateUSDModel(plugin.Creator):
    """Author USD Model"""

    label = "USD Model"
    family = "usdModel"
    icon = "gears"

    def process(self):

        node_type = "op::author_model:1.0"

        subset = self.data["subset"]
        name = "author_{}".format(subset)
        variant = re.match("usdModel(.*)", subset).group(1)

        # Get stage root and create node
        stage = hou.node("/stage")
        instance = stage.createNode(node_type, node_name=name)
        instance.moveToGoodPosition(move_unconnected=True)

        parms = {"asset_name": self.data["asset"], "variant_name": variant}

        # Set the Geo Path to the first selected node (if any)
        selection = hou.selectedNodes()
        if selection:
            node = selection[0]
            parms["geo_path"] = node.path()

        instance.setParms(parms)
