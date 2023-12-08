from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.gaffer.api import get_root, imprint_container
from openpype.hosts.gaffer.api.lib import set_node_color

import Gaffer


class GafferLoadReference(load.LoaderPlugin):
    """Reference a gaffer scene"""

    families = ["gafferScene"]
    representations = ["gfr"]

    label = "Reference Gaffer Scene"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        script = get_root()

        path = self.filepath_from_context(context).replace("\\", "/")

        reference = Gaffer.Reference(name)
        script.addChild(reference)
        reference.load(path)

        set_node_color(reference, (0.533, 0.447, 0.957))

        imprint_container(reference,
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
        node: Gaffer.Reference = container["_node"]
        node.load(path)

        # Update the imprinted representation
        node["user"]["representation"].SetValue(str(representation["_id"]))

    def remove(self, container):
        node = container["_node"]

        parent = node.parent()
        parent.removeChild(node)
