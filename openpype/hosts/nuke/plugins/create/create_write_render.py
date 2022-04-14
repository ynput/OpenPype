from collections import OrderedDict

import nuke

from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import create_write_node


class CreateWriteRender(plugin.OpenPypeCreator):
    # change this to template preset
    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    n_class = "Write"
    family = "render"
    icon = "sign-out"
    defaults = ["Main", "Mask"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        if self.presets.get('fpath_template'):
            self.log.info("Adding template path from preset")
            write_data.update(
                {"fpath_template": self.presets["fpath_template"]}
            )
        else:
            self.log.info("Adding template path from plugin")
            write_data.update({
                "fpath_template":
                    ("{work}/{}s/nuke/{subset}".format(self.family) +
                     "/{subset}.{frame}.{ext}")})

        write_node = self._create_write_node(selected_node,
                                             inputs, outputs,
                                             write_data)

        # relinking to collected connections
        for i, input in enumerate(inputs):
            write_node.setInput(i, input)

        write_node.autoplace()

        for output in outputs:
            output.setInput(0, write_node)

        write_node = self._modify_write_node(write_node)

        return write_node

    def _create_write_node(self, selected_node, inputs, outputs, write_data):
        # add reformat node to cut off all outside of format bounding box
        # get width and height
        try:
            width, height = (selected_node.width(), selected_node.height())
        except AttributeError:
            actual_format = nuke.root().knob('format').value()
            width, height = (actual_format.width(), actual_format.height())

        _prenodes = [
            {
                "name": "Reformat01",
                "class": "Reformat",
                "knobs": [
                    ("resize", 0),
                    ("black_outside", 1),
                ],
                "dependent": None
            }
        ]

        write_node = create_write_node(
            self.data["subset"],
            write_data,
            input=selected_node,
            prenodes=_prenodes)

        return write_node

    def _modify_write_node(self, write_node):
        return write_node