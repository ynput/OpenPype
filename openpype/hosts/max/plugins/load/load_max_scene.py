import os
from openpype.pipeline import (
    load, get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


class MaxSceneLoader(load.LoaderPlugin):
    """Max Scene Loader"""

    families = ["camera",
                "maxScene"]
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

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })
        max_objs_prev = []
        max_objs_after = []
        for c in rt.rootNode.Children:
            if rt.classOf(c) == rt.Container and c.startswith("maxSceneMain"):
                if c != container["instance_node"]:
                    max_objs_prev.append(c)
        rt.mergeMaxFile(path,
                        rt.Name("noRedraw"),
                        rt.Name("deleteOldDups"),
                        rt.Name("useSceneMtlDups"))
        for c in rt.rootNode.Children:
            if rt.classOf(c) == rt.Container and c.startswith("maxSceneMain"):
                if c != container["instance_node"]:
                    max_objs_after.append(c)

        max_obj = set(max_objs_after) - set(max_objs_prev)

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
