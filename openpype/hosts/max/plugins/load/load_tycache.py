import os
from openpype.hosts.max.api import lib, maintained_selection
from openpype.hosts.max.api.lib import (
    unique_namespace,

)
from openpype.hosts.max.api.pipeline import (
    containerise,
    get_previous_loaded_object,
    update_custom_attribute_data
)
from openpype.pipeline import get_representation_path, load


class TyCacheLoader(load.LoaderPlugin):
    """TyCache Loader."""

    families = ["tycache"]
    representations = ["tyc"]
    order = -8
    icon = "code-fork"
    color = "green"

    def load(self, context, name=None, namespace=None, data=None):
        """Load tyCache"""
        from pymxs import runtime as rt
        filepath = os.path.normpath(self.filepath_from_context(context))
        obj = rt.tyCache()
        obj.filename = filepath

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        obj.name = f"{namespace}:{obj.name}"

        return containerise(
            name, [obj], context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        """update the container"""
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.GetNodeByName(container["instance_node"])
        node_list = get_previous_loaded_object(node)
        update_custom_attribute_data(node, node_list)
        with maintained_selection():
            for tyc in node_list:
                tyc.filename = path
        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        """remove the container"""
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
