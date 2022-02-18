import nuke
from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import (
    set_avalon_knob_data
)


class CreateModel(plugin.OpenPypeCreator):
    """Add Publishable Model Geometry"""

    name = "model"
    label = "Create 3d Model"
    family = "model"
    icon = "cube"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateModel, self).__init__(*args, **kwargs)
        self.nodes = nuke.selectedNodes()
        self.node_color = "0xff3200ff"
        return

    def process(self):
        nodes = list()
        if (self.options or {}).get("useSelection"):
            nodes = self.nodes
            for n in nodes:
                n['selected'].setValue(0)
            end_nodes = list()

            # get the latest nodes in tree for selecion
            for n in nodes:
                x = n
                end = 0
                while end == 0:
                    try:
                        x = x.dependent()[0]
                    except:
                        end_node = x
                        end = 1
                end_nodes.append(end_node)

            # set end_nodes
            end_nodes = list(set(end_nodes))

            # check if nodes is 3d nodes
            for n in end_nodes:
                n['selected'].setValue(1)
                sn = nuke.createNode("Scene")
                if not sn.input(0):
                    end_nodes.remove(n)
                nuke.delete(sn)

            # loop over end nodes
            for n in end_nodes:
                n['selected'].setValue(1)

            self.nodes = nuke.selectedNodes()
            nodes = self.nodes
            if len(nodes) >= 1:
                # loop selected nodes
                for n in nodes:
                    data = self.data.copy()
                    if len(nodes) > 1:
                        # rename subset name only if more
                        # then one node are selected
                        subset = self.family + n["name"].value().capitalize()
                        data["subset"] = subset

                    # change node color
                    n["tile_color"].setValue(int(self.node_color, 16))
                    # add avalon knobs
                    set_avalon_knob_data(n, data)
                return True
            else:
                msg = str("Please select nodes you "
                          "wish to add to a container")
                self.log.error(msg)
                nuke.message(msg)
                return
        else:
            # if selected is off then create one node
            model_node = nuke.createNode("WriteGeo")
            model_node["tile_color"].setValue(int(self.node_color, 16))
            # add avalon knobs
            instance = set_avalon_knob_data(model_node, self.data)
            return instance
