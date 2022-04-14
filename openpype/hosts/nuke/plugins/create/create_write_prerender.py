import nuke

from openpype.hosts.nuke.api.lib import create_write_node
from openpype.hosts.nuke.plugins.create import create_write_render


class CreateWritePrerender(create_write_render.CreateWriteRender):
    # change this to template preset
    name = "WritePrerender"
    label = "Create Write Prerender"
    hosts = ["nuke"]
    n_class = "Write"
    family = "prerender"
    icon = "sign-out"
    defaults = ["Key01", "Bg01", "Fg01", "Branch01", "Part01"]

    def __init__(self, *args, **kwargs):
        super(CreateWritePrerender, self).__init__(*args, **kwargs)

    def _create_write_node(self, selected_node, inputs, outputs, write_data):
        reviewable = self.presets.get("reviewable")
        write_node = create_write_node(
            self.data["subset"],
            write_data,
            input=selected_node,
            prenodes=[],
            review=reviewable,
            linked_knobs=["channels", "___", "first", "last", "use_limit"])

        return write_node

    def _modify_write_node(self, write_node):
        # open group node
        write_node.begin()
        for n in nuke.allNodes():
            # get write node
            if n.Class() in "Write":
                w_node = n
        write_node.end()

        if self.presets.get("use_range_limit"):
            w_node["use_limit"].setValue(True)
            w_node["first"].setValue(nuke.root()["first_frame"].value())
            w_node["last"].setValue(nuke.root()["last_frame"].value())

        return write_node
