import os

from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.gaffer.api import get_root, imprint_container
from openpype.hosts.gaffer.api.lib import set_node_color


class GafferLoadArnoldVDB(load.LoaderPlugin):
    """Load VDB to Arnold"""

    families = ["vdbcache"]
    representations = ["vdb"]

    label = "Load VDB to Arnold"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        import GafferArnold

        # Create the Loader with the filename path set
        script = get_root()
        node = GafferArnold.ArnoldVDB()
        node.setName(name)

        path = self.fname.replace("\\", "/")
        node["fileName"].setValue(path)
        script.addChild(node)

        # Colorize based on family
        # TODO: Use settings instead
        set_node_color(node, (0.976, 0.212, 0))

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


if not os.environ.get("ARNOLD_ROOT"):
    # Arnold not set up for Gaffer - exclude the loader
    del GafferLoadArnoldVDB
