import os

from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.gaffer.api import get_root, imprint_container
from openpype.hosts.gaffer.api.lib import set_node_color

import GafferImage


class GafferLoadImage(load.LoaderPlugin):
    """Load Image or Image sequence"""

    families = ["imagesequence", "review", "render", "plate"]
    representations = ["*"]

    label = "Load sequence"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        # Create the Loader with the filename path set
        script = get_root()
        node = GafferImage.ImageReader()
        node.setName(name)

        path = self._convert_path(self.fname)
        node["fileName"].setValue(path)
        script.addChild(node)

        # Colorize based on family
        # TODO: Use settings instead
        set_node_color(node, (1, 0.98, 0.353))

        imprint_container(node,
                          name=name,
                          namespace=namespace,
                          context=context,
                          loader=self.__class__.__name__)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):

        path = get_representation_path(representation)
        path = self._convert_path(path)

        node = container["_node"]
        node["fileName"].setValue(path)

        # Update the imprinted representation
        node["user"]["representation"].SetValue(str(representation["_id"]))

    def remove(self, container):
        node = container["_node"]

        parent = node.parent()
        parent.removeChild(node)

    def _convert_path(self, path):
        root = os.path.dirname(path)
        fname = os.path.basename(path)

        # TODO: Actually detect whether it's a sequence. And support _ too.
        prefix, padding, suffix = fname.rsplit(".", 2)
        fname = ".".join([prefix, "#" * len(padding), suffix])
        return os.path.join(root, fname).replace("\\", "/")
