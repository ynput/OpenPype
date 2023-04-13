from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.openrv.api.pipeline import imprint_container
from openpype.hosts.openrv.api.commands import set_session_fps
from openpype.hosts.openrv.api.commands import reset_frame_range

import rv

class FramesLoader(load.LoaderPlugin):
    """Load frames into OpenRV"""

    label = "Load Frames"
    families = ["*"]
    representations = ["exr"]
    order = 0

    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        filepath = self.fname
        # Command fails on unicode so we must force it to be strings
        filepath = str(filepath)

        node_name = "{}_{}".format(namespace, name) if namespace else name
        namespace = namespace if namespace else context["asset"]["name"]

        set_session_fps()
        reset_frame_range()
        loaded_node = rv.commands.addSourceVerbose([filepath])
        print("loaded_node", loaded_node)
        imprint_container(
            loaded_node,
            name=name,
            namespace=namespace,
            context=context,
            loader=self.__class__.__name__
        )



    def update(self, container, representation):
        node = container["node"]
        filepath = get_representation_path(representation)
        filepath = str(filepath)
        set_session_fps()
        reset_frame_range()
        # change path
        rv.commands.setSourceMedia(node, [filepath])
        rv.commands.setStringProperty(node + ".media.name", ["newname"], True)
        rv.commands.setStringProperty(node + ".media.repName", ["repname"], True)
        rv.commands.setStringProperty(node + ".openpype.representation", [str(representation["_id"])], True)



    def remove(self, container):
        node = container["node"]
        # not implemented
        return

