import os
from openpype.pipeline import (
    load, get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


class MaxSceneLoader(load.LoaderPlugin):
    """Max Scene Loader"""

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

        merge_before = {
            c for c in rt.rootNode.Children
            if rt.classOf(c) == rt.Container
        }
        rt.mergeMaxFile(path)

        merge_after = {
            c for c in rt.rootNode.Children
            if rt.classOf(c) == rt.Container
        }
        max_containers = merge_after.difference(merge_before)

        if len(max_containers) != 1:
            self.log.error("Something failed when loading.")

        max_container = max_containers.pop()

        return containerise(
            name, [max_container], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])
        max_objects = node.Children
        for max_object in max_objects:
            max_object.source = path

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
