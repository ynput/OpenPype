from openpype.pipeline import (
    load,
    get_representation_context
)
from openpype.hosts.openrv.api.pipeline import imprint_container
from openpype.hosts.openrv.api.ocio import (
    set_group_ocio_active_state,
    set_group_ocio_colorspace
)

import rv


class MovLoader(load.LoaderPlugin):
    """Load mov into OpenRV"""

    label = "Load MOV"
    families = ["*"]
    representations = ["*"]
    extensions = ["mov", "mp4"]
    order = 0

    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        filepath = self.fname
        # Command fails on unicode so we must force it to be strings
        filepath = str(filepath)

        # node_name = "{}_{}".format(namespace, name) if namespace else name
        namespace = namespace if namespace else context["asset"]["name"]

        loaded_node = rv.commands.addSourceVerbose([filepath])

        # update colorspace
        self.set_representation_colorspace(loaded_node,
                                           context["representation"])

        imprint_container(
            loaded_node,
            name=name,
            namespace=namespace,
            context=context,
            loader=self.__class__.__name__
        )

    def update(self, container, representation):
        node = container["node"]

        context = get_representation_context(representation)
        filepath = load.get_representation_path_from_context(context)
        filepath = str(filepath)

        # change path
        rv.commands.setSourceMedia(node, [filepath])

        # update colorspace
        self.set_representation_colorspace(node, context["representation"])

        # update name
        rv.commands.setStringProperty(node + ".media.name",
                                      ["newname"], True)
        rv.commands.setStringProperty(node + ".media.repName",
                                      ["repname"], True)
        rv.commands.setStringProperty(node + ".openpype.representation",
                                      [str(representation["_id"])], True)

    def remove(self, container):
        node = container["node"]
        group = rv.commands.nodeGroup(node)
        rv.commands.deleteNode(group)

    def set_representation_colorspace(self, node, representation):
        colorspace_data = representation.get("data", {}).get("colorspaceData")
        if colorspace_data:
            colorspace = colorspace_data["colorspace"]
            # TODO: Confirm colorspace is valid in current OCIO config
            #   otherwise errors will be spammed from OpenRV for invalid space

            self.log.info(f"Setting colorspace: {colorspace}")
            group = rv.commands.nodeGroup(node)

            # Enable OCIO for the node and set the colorspace
            set_group_ocio_active_state(group, state=True)
            set_group_ocio_colorspace(group, colorspace)
