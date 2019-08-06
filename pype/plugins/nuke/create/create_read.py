from collections import OrderedDict
import avalon.api
import avalon.nuke
from pype import api as pype

import nuke


log = pype.Logger().get_logger(__name__, "nuke")


class CrateRead(avalon.nuke.Creator):
    # change this to template preset
    name = "ReadCopy"
    label = "Create Read Copy"
    hosts = ["nuke"]
    family = "source"
    families = family
    icon = "film"

    def __init__(self, *args, **kwargs):
        super(CrateRead, self).__init__(*args, **kwargs)

        data = OrderedDict()
        data['family'] = self.family
        data['families'] = self.families
        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        self.name = self.data["subset"]

        nodes = nuke.selectedNodes()

        if not nodes or len(nodes) == 0:
            nuke.message('Please select Read node')
        else:
            count_reads = 0
            for node in nodes:
                if node.Class() != 'Read':
                    continue
                name = node["name"].value()
                avalon_data = self.data
                avalon_data['subset'] = "{}_{}".format(self.family, name)
                self.change_read_node(self.data["subset"], node, avalon_data)
                count_reads += 1

            if count_reads < 1:
                nuke.message('Please select Read node')
        return

    def change_read_node(self, name, node, data):
        node = avalon.nuke.lib.imprint(node, data)
        node['tile_color'].setValue(16711935)
