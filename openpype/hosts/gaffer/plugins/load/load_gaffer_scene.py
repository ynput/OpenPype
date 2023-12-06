from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.gaffer.api import get_root, imprint_container
from openpype.hosts.gaffer.api.lib import set_node_color

import Gaffer


def import_file(script: Gaffer.ScriptNode, filepath: str):

    with Gaffer.UndoScope(script):

        new_children = []

        def acquire_new_nodes(parent, child):
            new_children.append(child)

        callback = script.childAddedSignal().connect(
            acquire_new_nodes, scoped=True
        )

        script.importFile(str(filepath),
                          parent=script,
                          continueOnError=True)

        new_nodes = [c for c in new_children if isinstance(c, Gaffer.Node)]
        script.selection().clear()
        script.selection().add(new_nodes)

        del callback

        return new_children

class GafferLoadScene(load.LoaderPlugin):
    """Import a gaffer scene"""

    families = ["gafferScene"]
    representations = ["gfr"]

    label = "Load gaffer scene"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        script = get_root()

        # Import gaffer sccene
        path = self.filepath_from_context(context).replace("\\", "/")
        new_nodes = import_file(script, path)

        assert len(new_nodes) == 1, "Only one new node allowed"

        # Colorize based on family
        # TODO: Use settings instead
        node = new_nodes[0]
        set_node_color(node, (0.533, 0.447, 0.957))

        imprint_container(node,
                          name=name,
                          namespace=namespace,
                          context=context,
                          loader=self.__class__.__name__)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):

        path = get_representation_path(representation)
        path = path.replace("\\", "/")

        # This is where things get tricky - do we just remove the node
        # completely and replace it with a new one? For now we do. Preferably
        # however we would have it like a 'reference' so that we can just
        # update the loaded 'box' or 'contents' to the new one.
        node = container["_node"]

        # Delete self
        parent = node.parent()
        parent.removeChild(node)

        new_node = import_file(parent, path)

        # Can we just copy this?
        for plug in node["user"]:
            new_node["user"][plug.getName()] = plug

        # Update the imprinted representation
        node["user"]["representation"].SetValue(str(representation["_id"]))

    def remove(self, container):
        node = container["_node"]

        parent = node.parent()
        parent.removeChild(node)
