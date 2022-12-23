from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.gaffer.api import get_root, imprint_container

import GafferScene


class GafferLoadScene(load.LoaderPlugin):
    """Load Scene"""

    families = ["pointcache", "model"]
    representations = ["abc"]

    label = "Load scene"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        # Create the Loader with the filename path set
        script = get_root()
        node = GafferScene.SceneReader()
        node.setName(name)

        path = self.fname.replace("\\", "/")
        node["fileName"].setValue(path)
        script.addChild(node)

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

        node = container["_node"]
        node["fileName"].setValue(path)

        # Update the imprinted representation
        node["user"]["representation"].SetValue(str(representation["_id"]))

    def remove(self, container):
        node = container["_node"]

        parent = node.parent()
        parent.removeChild(node)