from collections import OrderedDict
from pype.hosts.nuke import (
    plugin,
    lib as pnlib)
import nuke


class CreateWriteRender(plugin.PypeCreator):
    # change this to template preset
    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    n_class = "write"
    family = "render"
    icon = "sign-out"
    defaults = ["Main", "Mask"]

    def __init__(self, *args, **kwargs):
        super(CreateWriteRender, self).__init__(*args, **kwargs)

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

            if len(nodes) == 0:
                msg = (
                    "No nodes selected. Please select a single node to connect"
                    " to or tick off `Use selection`"
                )
                self.log.error(msg)
                nuke.message(msg)

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
            "class": self.n_class,
            "families": [self.family],
            "avalon": self.data
        }

        if self.presets.get('fpath_template'):
            self.log.info("Adding template path from preset")
            write_data.update(
                {"fpath_template": self.presets["fpath_template"]}
            )
        else:
            self.log.info("Adding template path from plugin")
            write_data.update({
                "fpath_template": ("{work}/renders/nuke/{subset}"
                                   "/{subset}.{frame}.{ext}")})

        write_node = pnlib.create_write_node(
            self.data["subset"],
            write_data,
            input=selected_node)

        # relinking to collected connections
        for i, input in enumerate(inputs):
            write_node.setInput(i, input)

        write_node.autoplace()

        for output in outputs:
            output.setInput(0, write_node)

        return write_node
