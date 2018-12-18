from collections import OrderedDict
import avalon.api
import avalon.nuke
from pype.nuke import create_write_node
from pype import api as pype

import nuke


log = pype.Logger.getLogger(__name__, "nuke")


class CrateRead(avalon.nuke.Creator):
    # change this to template preset
    name = "ReadCopy"
    label = "Create Read Copy"
    hosts = ["nuke"]
    # family = "read"
    family = "source"
    icon = "sign-out"

    def __init__(self, *args, **kwargs):
        super(CrateRead, self).__init__(*args, **kwargs)

        data = OrderedDict()
        data['family'] = self.family

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        self.name = self.data["subset"]

        nodes = nuke.selectedNodes()

        if not nodes:
            nuke.message('Please select Read node')
        elif len(nodes) == 1:
            if nodes[0].Class() != 'Read':
                nuke.message('Please select Read node')
            else:

                node = nodes[0]
                name = node["name"].value()
                avalon_data = self.data
                avalon_data['subset'] = "{}_{}".format(self.family, name)
                change_read_node(self.data["subset"], node, avalon_data)
        else:
            nuke.message('Please select only one Read node')
        return


def change_read_node(name, node, data):
    node = avalon.nuke.lib.imprint(node, data)
    node['tile_color'].setValue(16711935)
