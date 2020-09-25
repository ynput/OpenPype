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
        self.node_color = "0xdfea5dff"
        return

    def process(self):
        nodes = list()
        if (self.options or {}).get("useSelection"):
            nodes = self.nodes

            if len(nodes) >= 1:
                anlib.select_nodes(nodes)
                # camera_node = autoBackdrop()
                # camera_node["name"].setValue("{}_BDN".format(self.name))
                # camera_node["tile_color"].setValue(int(self.node_color, 16))
                # camera_node["note_font_size"].setValue(24)
                # camera_node["label"].setValue("[{}]".format(self.name))
                # # add avalon knobs
                # instance = anlib.imprint(camera_node, self.data)
                #
                # return instance
            else:
                msg = str("Please select nodes you "
                          "wish to add to a container")
                self.log.error(msg)
                nuke.message(msg)
                return
        else:
            camera_node = autoBackdrop()
            camera_node["name"].setValue("{}_BDN".format(self.name))
            camera_node["tile_color"].setValue(int(self.node_color, 16))
            camera_node["note_font_size"].setValue(24)
            camera_node["label"].setValue("[{}]".format(self.name))
            # add avalon knobs
            instance = anlib.imprint(camera_node, self.data)

            return instance
