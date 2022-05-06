import nuke

from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import create_write_node


class CreateWriteStill(plugin.AbstractWriteRender):
    # change this to template preset
    name = "WriteStillFrame"
    label = "Create Write Still Image"
    hosts = ["nuke"]
    n_class = "Write"
    family = "still"
    icon = "image"

    # settings
    fpath_template = "{work}/render/nuke/{subset}/{subset}.{ext}"
    defaults = [
        "ImageFrame",
        "MPFrame",
        "LayoutFrame"
    ]
    prenodes = {
        "FrameHold01": {
            "nodeclass": "FrameHold",
            "dependent": None,
            "knobs": [
                {
                    "type": "formatable",
                    "name": "first_frame",
                    "template": "{frame}",
                    "to_type": "number"
                }
            ]
        }
    }

    def __init__(self, *args, **kwargs):
        super(CreateWriteStill, self).__init__(*args, **kwargs)

    def _create_write_node(self, selected_node, inputs, outputs, write_data):
        # add fpath_template
        write_data["fpath_template"] = self.fpath_template

        return create_write_node(
            self.name,
            write_data,
            input=selected_node,
            review=False,
            prenodes=self.prenodes,
            farm=False,
            linked_knobs=["channels", "___", "first", "last", "use_limit"],
            **{
                "frame": nuke.frame()
            }
        )

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
