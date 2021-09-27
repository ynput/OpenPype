# -*- coding: utf-8 -*-
from openpype.hosts.houdini.api import plugin
from avalon.houdini import lib
import hou


class CreateHDA(plugin.Creator):
    """Publish Houdini Digital Asset file."""

    name = "hda"
    label = "Houdini Digital Asset (Hda)"
    family = "hda"
    icon = "gears"
    maintain_selection = False

    def __init__(self, *args, **kwargs):
        super(CreateHDA, self).__init__(*args, **kwargs)
        self.data.pop("active", None)

    def _process(self, instance):

        out = hou.node("/obj")
        self.nodes = hou.selectedNodes()

        if (self.options or {}).get("useSelection") and self.nodes:
            to_hda = self.nodes[0]
            if len(self.nodes) > 1:
                subnet = out.createNode(
                    "subnet", node_name="{}_subnet".format(self.name))
                to_hda = subnet
        else:
            subnet = out.createNode(
                "subnet", node_name="{}_subnet".format(self.name))
            subnet.moveToGoodPosition()
            to_hda = subnet

        hda_node = to_hda.createDigitalAsset(
            name=self.name,
            hda_file_name="$HIP/{}.hda".format(self.name)
        )
        hda_node.setName(self.name)
        hou.moveNodesTo(self.nodes, hda_node)
        hda_node.layoutChildren()
        # delete node created by Avalon in /out
        # this needs to be addressed in future Houdini workflow refactor.
        hou.node("/out/{}".format(self.name)).destroy()

        lib.imprint(hda_node, self.data)

        return hda_node
