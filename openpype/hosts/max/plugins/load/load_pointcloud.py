import os

from openpype.hosts.max.api import lib, maintained_selection
from openpype.hosts.max.api.lib import unique_namespace
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
        prt_container = rt.GetNodeByName(obj.name)
        prt_container = rt.container()
        prt_container.name = name
        obj.Parent = prt_container
        import_custom_attribute_data(prt_container, [obj])

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )

        return containerise(
            name, [prt_container], context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        """update the container"""
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.GetNodeByName(container["instance_node"])
        with maintained_selection():
            rt.Select(node.Children)
            for prt in rt.Selection:
                prt_object = rt.GetNodeByName(prt.name)
                prt_object.filename = path
        update_custom_attribute_data(node, node.Children)
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
