from avalon.nuke import lib as anlib
from openpype.hosts.nuke.api import plugin
import nuke


class CreateModel(plugin.PypeCreator):
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
                    anlib.set_avalon_knob_data(n, data)
                return True
            else:
                msg = str("Please select nodes you "
                          "wish to add to a container")
                self.log.error(msg)
                nuke.message(msg)
                return
        else:
            # if selected is off then create one node
            model_node = nuke.createNode("Model2")
            model_node["tile_color"].setValue(int(self.node_color, 16))
            # add avalon knobs
            instance = anlib.set_avalon_knob_data(model_node, self.data)
            return instance
