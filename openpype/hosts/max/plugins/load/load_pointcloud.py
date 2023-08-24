import os

from openpype.hosts.max.api import lib, maintained_selection
from openpype.hosts.max.api.lib import (
    unique_namespace, get_namespace
)
from openpype.hosts.max.api.pipeline import (
    containerise,
    import_custom_attribute_data,
    update_custom_attribute_data
)
from openpype.pipeline import get_representation_path, load


class PointCloudLoader(load.LoaderPlugin):
    """Point Cloud Loader."""

    families = ["pointcloud"]
    representations = ["prt"]
    order = -8
    icon = "code-fork"
    color = "green"

    def load(self, context, name=None, namespace=None, data=None):
        """load point cloud by tyCache"""
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.filepath_from_context(context))
        obj = rt.tyCache()
        obj.filename = filepath

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        prt_container = rt.Container(name=f"{namespace}:{name}")
        import_custom_attribute_data(prt_container, [obj])
        obj.Parent = prt_container
        obj.name = f"{namespace}:{obj.name}"

        return containerise(
            name, [prt_container], context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        """update the container"""
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.GetNodeByName(container["instance_node"])
        namespace, name = get_namespace(container["instance_node"])
        sub_node_name = f"{namespace}:{name}"
        inst_container = rt.getNodeByName(sub_node_name)
        update_custom_attribute_data(
            inst_container, inst_container.Children)
        with maintained_selection():
            rt.Select(node.Children)
            for prt in inst_container.Children:
                prt.filename = path
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
