import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.pipeline import containerise
from openpype.pipeline import get_representation_path, load


class MaxSceneLoader(load.LoaderPlugin):
    """Max Scene Loader."""

    families = ["camera",
                "maxScene",
                "model"]

    representations = ["max"]
    order = -8
    icon = "code-fork"
    color = "green"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt
        path = os.path.normpath(self.fname)
        # import the max scene by using "merge file"
        path = path.replace('\\', '/')

        merge_before = set(rt.RootNode.Children)
        rt.MergeMaxFile(path)

        merge_after = set(rt.RootNode.Children)
        max_objects = merge_after.difference(merge_before)
        max_container = rt.Container(name=f"{name}")
        for max_object in max_objects:
            max_object.Parent = max_container

        return containerise(
            name, [max_container], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        instance_name, _ = node_name.split("_")
        merge_before = set(rt.RootNode.Children)
        rt.MergeMaxFile(path,
                        rt.Name("noRedraw"),
                        rt.Name("deleteOldDups"),
                        rt.Name("useSceneMtlDups"))
        merge_after = set(rt.EootNode.Children)
        max_objects = merge_after.difference(merge_before)
        container_node = rt.GetNodeByName(instance_name)
        for max_object in max_objects:
            max_object.Parent = container_node

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
