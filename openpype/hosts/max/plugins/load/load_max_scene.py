import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.pipeline import containerise, loadOpenpypeData
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
        # implement the OP attributes before load
        loadOpenpypeData()
        path = self.filepath_from_context(context)
        path = os.path.normpath(path)
        # import the max scene by using "merge file"
        path = path.replace('\\', '/')
        rt.MergeMaxFile(path)
        max_objects = [obj for obj in rt.getLastMergedNodes()
                       if rt.classOf(obj) != rt.Container]
        max_container = [obj for obj in rt.getLastMergedNodes()
                         if rt.classOf(obj) == rt.Container]
        for max_object in max_objects:
            max_object.Parent = max_container[0]

        return containerise(
            name, max_container, context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)

        rt.MergeMaxFile(path)

        max_objects = rt.getLastMergedNodes()
        max_objects = [obj for obj in rt.getLastMergedNodes()
                       if rt.classOf(obj) != rt.Container]
        max_container = [obj for obj in rt.getLastMergedNodes()
                         if rt.classOf(obj) == rt.Container]
        for max_object in max_objects:
            max_object.Parent = max_container[0]

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
