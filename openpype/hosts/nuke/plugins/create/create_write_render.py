import nuke

from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import create_write_node


class CreateWriteRender(plugin.AbstractWriteRender):
    # change this to template preset
    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    n_class = "Write"
    family = "render"
    icon = "sign-out"
    defaults = ["Main", "Mask"]
    knobs = []

    def __init__(self, *args, **kwargs):
        super(CreateWriteRender, self).__init__(*args, **kwargs)

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

        return create_write_node(
            self.data["subset"],
            write_data,
            input=selected_node,
            prenodes=_prenodes
        )

    def _modify_write_node(self, write_node):
        return write_node
