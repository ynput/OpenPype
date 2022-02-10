from collections import OrderedDict

import nuke

from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import create_write_node


class CreateWriteStill(plugin.OpenPypeCreator):
    # change this to template preset
    name = "WriteStillFrame"
    label = "Create Write Still Image"
    hosts = ["nuke"]
    n_class = "Write"
    family = "still"
    icon = "image"
    defaults = [
        "ImageFrame{:0>4}".format(nuke.frame()),
        "MPFrame{:0>4}".format(nuke.frame()),
        "LayoutFrame{:0>4}".format(nuke.frame())
    ]

    def __init__(self, *args, **kwargs):
        super(CreateWriteStill, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family
        data["families"] = self.n_class

        for k, v in self.data.items():
            if k not in data.keys():
                data.update({k: v})

        self.data = data
        self.nodes = nuke.selectedNodes()
        self.log.debug("_ self.data: '{}'".format(self.data))

    def process(self):

        inputs = []
        outputs = []
        instance = nuke.toNode(self.data["subset"])
        selected_node = None

        # use selection
        if (self.options or {}).get("useSelection"):
            nodes = self.nodes

            if not (len(nodes) < 2):
                msg = ("Select only one node. "
                       "The node you want to connect to, "
                       "or tick off `Use selection`")
                self.log.error(msg)
                nuke.message(msg)
                return

            if len(nodes) == 0:
                msg = (
                    "No nodes selected. Please select a single node to connect"
                    " to or tick off `Use selection`"
                )
                self.log.error(msg)
                nuke.message(msg)
                return

            selected_node = nodes[0]
            inputs = [selected_node]
            outputs = selected_node.dependent()

            if instance:
                if (instance.name() in selected_node.name()):
                    selected_node = instance.dependencies()[0]

        # if node already exist
        if instance:
            # collect input / outputs
            inputs = instance.dependencies()
            outputs = instance.dependent()
            selected_node = inputs[0]
            # remove old one
            nuke.delete(instance)

        # recreate new
        write_data = {
            "nodeclass": self.n_class,
            "families": [self.family],
            "avalon": self.data
        }

        # add creator data
        creator_data = {"creator": self.__class__.__name__}
        self.data.update(creator_data)
        write_data.update(creator_data)

        self.log.info("Adding template path from plugin")
        write_data.update({
            "fpath_template": (
                "{work}/renders/nuke/{subset}/{subset}.{ext}")})

        _prenodes = [
            {
                "name": "FrameHold01",
                "class": "FrameHold",
                "knobs": [
                    ("first_frame", nuke.frame())
                ],
                "dependent": None
            }
        ]

        write_node = create_write_node(
            self.name,
            write_data,
            input=selected_node,
            review=False,
            prenodes=_prenodes,
            farm=False,
            linked_knobs=["channels", "___", "first", "last", "use_limit"])

        # relinking to collected connections
        for i, input in enumerate(inputs):
            write_node.setInput(i, input)

        write_node.autoplace()

        for output in outputs:
            output.setInput(0, write_node)

        # link frame hold to group node
        write_node.begin()
        for n in nuke.allNodes():
            # get write node
            if n.Class() in "Write":
                w_node = n
        write_node.end()

        w_node["use_limit"].setValue(True)
        w_node["first"].setValue(nuke.frame())
        w_node["last"].setValue(nuke.frame())

        return write_node
