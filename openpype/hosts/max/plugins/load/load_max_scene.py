import os
from openpype.pipeline import(
    load
)

class MaxSceneLoader(load.LoaderPlugin):
    """Max Scene Loader"""

    families = ["camera"]
    representations = ["max"]
    order = -8
    icon = "code-fork"
    color = "green"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt
        import re
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
        container_name = f"{name}_CON"
        # rename the container with "_CON"
        # get the original container
        container = rt.container(name=container_name)
        max_container.Parent = container

        return container

    def remove(self, container):
        from pymxs import runtime as rt

        node = container["node"]
        rt.delete(node)

