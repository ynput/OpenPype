import os
import clique

from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


class RedshiftProxyLoader(load.LoaderPlugin):

    """Load rs files with Redshift Proxy"""

    label = "Load Redshift Proxy"
    families = ["redshiftproxy"]
    representations = ["rs"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        filepath = self.filepath_from_context(context)
        rs_proxy = rt.RedshiftProxy()
        rs_proxy.file = filepath
        files_in_folder = os.listdir(os.path.dirname(filepath))
        collections, remainder = clique.assemble(files_in_folder)
        if collections:
            rs_proxy.is_sequence = True

        container = rt.container()
        container.name = name
        rs_proxy.Parent = container

        asset = rt.getNodeByName(f"{name}")

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])

        proxy_objects = self.get_container_children(node)
        for proxy in proxy_objects:
            proxy.source = path

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
