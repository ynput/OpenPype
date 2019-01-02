from collections import OrderedDict
import avalon.api
import avalon.nuke
from pype import api as pype

import nuke


log = pype.Logger.getLogger(__name__, "nuke")


class CrateRead(avalon.nuke.Creator):
    # change this to template preset
    name = "ReadCopy"
    label = "Create Read Copy"
    hosts = ["nuke"]
    family = "source"
    families = family
    icon = "sign-out"

    def __init__(self, *args, **kwargs):
        super(CrateRead, self).__init__(*args, **kwargs)

        data = OrderedDict()
        data['family'] = self.family
        data['families'] = self.family
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
        node = self.add_transfer_knob(node)
        node['tile_color'].setValue(16711935)

    def add_transfer_knob(self, node):
        knob_name = "transferSource"
        knob_label = "Transfer"
        if knob_name not in node.knobs():
            knob = nuke.Boolean_Knob(knob_name, knob_label)
            knob.setValue(True)
            knob.setFlag(nuke.STARTLINE)
            node.addKnob(knob)
        return node
