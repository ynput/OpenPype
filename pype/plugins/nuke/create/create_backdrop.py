import avalon.nuke
from avalon.nuke import lib as anlib
import nuke


class CreateBackdrop(avalon.nuke.Creator):
    """Add Publishable Backdrop"""

    name = "nukenodes"
    label = "Create Backdrop"
    family = "nukenodes"
    icon = "file-archive-o"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateBackdrop, self).__init__(*args, **kwargs)
        self.nodes = nuke.selectedNodes()
        self.node_color = "0xdfea5dff"
        return

    def process(self):
        from nukescripts import autoBackdrop
        nodes = list()
        if (self.options or {}).get("useSelection"):
            nodes = self.nodes

            if len(nodes) >= 1:
                anlib.select_nodes(nodes)
                bckd_node = autoBackdrop()
                bckd_node["name"].setValue("{}_BDN".format(self.name))
                bckd_node["tile_color"].setValue(int(self.node_color, 16))
                bckd_node["note_font_size"].setValue(24)
                bckd_node["label"].setValue("[{}]".format(self.name))
                # add avalon knobs
                instance = anlib.imprint(bckd_node, self.data)

                return instance
            else:
                msg = str("Please select nodes you "
                          "wish to add to a container")
                self.log.error(msg)
                nuke.message(msg)
                return
        else:
            bckd_node = autoBackdrop()
            bckd_node["name"].setValue("{}_BDN".format(self.name))
            bckd_node["tile_color"].setValue(int(self.node_color, 16))
            bckd_node["note_font_size"].setValue(24)
            bckd_node["label"].setValue("[{}]".format(self.name))
            # add avalon knobs
            instance = anlib.imprint(bckd_node, self.data)

            return instance
