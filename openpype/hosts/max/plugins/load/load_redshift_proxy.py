import os
import clique

from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise, load_OpenpypeData
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
        load_OpenpypeData(container, [rs_proxy])
        asset = rt.getNodeByName(name)

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])
        for children in node.Children:
            children_node = rt.getNodeByName(children.name)
            for proxy in children_node.Children:
                proxy.file = path

        load_OpenpypeData(node, node.Children)
        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
