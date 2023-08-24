import os
import clique

from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.max.api.pipeline import (
    containerise,
    import_custom_attribute_data,
    update_custom_attribute_data
)
from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    unique_namespace, get_namespace
)


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


        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        container = rt.Container(name=f"{namespace}:{name}")
        rs_proxy.Parent = container
        rs_proxy.name = f"{namespace}:{rs_proxy.name}"
        import_custom_attribute_data(container, [rs_proxy])

        return containerise(
            name, [container], context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        namespace, name = get_namespace(container["instance_node"])
        sub_node_name = f"{namespace}:{name}"
        inst_container = rt.getNodeByName(sub_node_name)

        update_custom_attribute_data(
            inst_container, inst_container.Children)
        for proxy in inst_container.Children:
            proxy.file = path

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
