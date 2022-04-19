import nuke

from openpype.hosts.nuke.api.lib import create_write_node
from openpype.hosts.nuke.plugins.create import create_write_render


class CreateWriteStill(create_write_render.CreateWriteRender):
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

    def _create_write_node(self, selected_node, inputs, outputs, write_data):
        # explicitly reset template to 'renders', not same as other 2 writes
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

        return write_node

    def _modify_write_node(self, write_node):
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
