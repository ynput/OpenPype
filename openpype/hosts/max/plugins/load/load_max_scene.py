import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.pipeline import containerise, load_OpenpypeData

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

        path = self.filepath_from_context(context)
        path = os.path.normpath(path)
        # import the max scene by using "merge file"
        path = path.replace('\\', '/')
        rt.MergeMaxFile(path)
        max_objects = rt.getLastMergedNodes()
        max_container = rt.Container(name=f"{name}")
        load_OpenpypeData(max_container, max_objects)
        for max_object in max_objects:
            max_object.Parent = max_container

        return containerise(
            name, [max_container], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]

        rt.MergeMaxFile(path)

        max_objects = rt.getLastMergedNodes()
        container_node = rt.GetNodeByName(node_name)
        instance_name, _ = os.path.splitext(node_name)
        instance_container = rt.GetNodeByName(instance_name)
        for max_object in max_objects:
            max_object.Parent = instance_container
        instance_container.Parent = container_node
        load_OpenpypeData(container_node, max_objects)
        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
