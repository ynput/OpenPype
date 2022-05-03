import nuke

from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import create_write_node


class CreateWritePrerender(plugin.AbstractWriteRender):
    # change this to template preset
    name = "WritePrerender"
    label = "Create Write Prerender"
    hosts = ["nuke"]
    n_class = "Write"
    family = "prerender"
    icon = "sign-out"

    # settings
    fpath_template = "{work}/render/nuke/{subset}/{subset}.{frame}.{ext}"
    defaults = ["Key01", "Bg01", "Fg01", "Branch01", "Part01"]
    reviewable = False
    use_range_limit = True

    def __init__(self, *args, **kwargs):
        super(CreateWritePrerender, self).__init__(*args, **kwargs)

    def _create_write_node(self, selected_node, inputs, outputs, write_data):
        # add fpath_template
        write_data["fpath_template"] = self.fpath_template

        return create_write_node(
            self.data["subset"],
            write_data,
            input=selected_node,
            review=self.reviewable,
            linked_knobs=["channels", "___", "first", "last", "use_limit"]
        )

    def _modify_write_node(self, write_node):
        # open group node
        write_node.begin()
        for n in nuke.allNodes():
            # get write node
            if n.Class() in "Write":
                w_node = n
        write_node.end()

        if self.use_range_limit:
            w_node["use_limit"].setValue(True)
            w_node["first"].setValue(nuke.root()["first_frame"].value())
            w_node["last"].setValue(nuke.root()["last_frame"].value())

        return write_node
