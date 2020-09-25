import avalon.nuke
from avalon.nuke import lib as anlib
import nuke


class CreateCamera(avalon.nuke.Creator):
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
                for n in nodes:
                    data = self.data.copy()
                    subset = self.family + n["name"].value().capitalize()
                    data["subset"] = subset
                    n["tile_color"].setValue(int(self.node_color, 16))
                    # add avalon knobs
                    anlib.imprint(n, data)
            else:
                msg = str("Please select nodes you "
                          "wish to add to a container")
                self.log.error(msg)
                nuke.message(msg)
                return
        else:
            camera_node = nuke.createNode("Camera2")
            camera_node["tile_color"].setValue(int(self.node_color, 16))
            # add avalon knobs
            instance = anlib.imprint(camera_node, self.data)
            return instance
