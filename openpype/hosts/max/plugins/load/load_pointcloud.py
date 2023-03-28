import os
from openpype.pipeline import (
    load, get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import maintained_selection


class PointCloudLoader(load.LoaderPlugin):
    """Point Cloud Loader"""

    families = ["pointcloud"]
    representations = ["prt"]
    order = -8
    icon = "code-fork"
    color = "green"

    def load(self, context, name=None, namespace=None, data=None):
        """load point cloud by tyCache"""
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.fname)
        obj = rt.tyCache()
        obj.filename = filepath

        prt_container = rt.getNodeByName(f"{obj.name}")

        return containerise(
            name, [prt_container], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        """update the container"""
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])
        rt.select(node.Children)
        for prt in rt.selection:
            prt_object = rt.getNodeByName(prt.name)
            prt_object.filename = path

        with maintained_selection():
            rt.select(node)

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        """remove the container"""
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
