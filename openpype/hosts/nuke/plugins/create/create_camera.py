import nuke
from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import (
    set_avalon_knob_data
)


class CreateCamera(plugin.OpenPypeCreator):
    """Add Publishable Backdrop"""

    name = "camera"
    label = "Create 3d Camera"
    family = "camera"
    icon = "camera"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateCamera, self).__init__(*args, **kwargs)
        self.nodes = nuke.selectedNodes()
        self.node_color = "0xff9100ff"
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
            camera_node = nuke.createNode("Camera2")
            camera_node["tile_color"].setValue(int(self.node_color, 16))
            # add avalon knobs
            instance = set_avalon_knob_data(camera_node, self.data)
            return instance
