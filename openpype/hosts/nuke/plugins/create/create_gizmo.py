import nuke

from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import (
    maintained_selection,
    select_nodes,
    set_avalon_knob_data
)


class CreateGizmo(plugin.OpenPypeCreator):
    """Add Publishable "gizmo" group

    The name is symbolically gizmo as presumably
    it is something familiar to nuke users as group of nodes
    distributed downstream in workflow
    """

    name = "gizmo"
    label = "Gizmo"
    family = "gizmo"
    icon = "file-archive-o"
    defaults = ["ViewerInput", "Lut", "Effect"]

    def __init__(self, *args, **kwargs):
        super(CreateGizmo, self).__init__(*args, **kwargs)
        self.nodes = nuke.selectedNodes()
        self.node_color = "0x7533c1ff"
        return

    def process(self):
        if (self.options or {}).get("useSelection"):
            nodes = self.nodes
            self.log.info(len(nodes))
            if len(nodes) == 1:
                select_nodes(nodes)
                node = nodes[-1]
                # check if Group node
                if node.Class() in "Group":
                    node["name"].setValue("{}_GZM".format(self.name))
                    node["tile_color"].setValue(int(self.node_color, 16))
                    return set_avalon_knob_data(node, self.data)
                else:
                    msg = ("Please select a group node "
                          "you wish to publish as the gizmo")
                    self.log.error(msg)
                    nuke.message(msg)

            if len(nodes) >= 2:
                select_nodes(nodes)
                nuke.makeGroup()
                gizmo_node = nuke.selectedNode()
                gizmo_node["name"].setValue("{}_GZM".format(self.name))
                gizmo_node["tile_color"].setValue(int(self.node_color, 16))

                # add sticky node with guide
                with gizmo_node:
                    sticky = nuke.createNode("StickyNote")
                    sticky["label"].setValue(
                        "Add following:\n- set Input"
                        " nodes\n- set one Output1\n"
                        "- create User knobs on the group")

                # add avalon knobs
                return set_avalon_knob_data(gizmo_node, self.data)

            else:
                msg = "Please select nodes you wish to add to the gizmo"
                self.log.error(msg)
                nuke.message(msg)
                return
        else:
            with maintained_selection():
                gizmo_node = nuke.createNode("Group")
                gizmo_node["name"].setValue("{}_GZM".format(self.name))
                gizmo_node["tile_color"].setValue(int(self.node_color, 16))

                # add sticky node with guide
                with gizmo_node:
                    sticky = nuke.createNode("StickyNote")
                    sticky["label"].setValue(
                        "Add following:\n- add Input"
                        " nodes\n- add one Output1\n"
                        "- create User knobs on the group")

                # add avalon knobs
                return set_avalon_knob_data(gizmo_node, self.data)
