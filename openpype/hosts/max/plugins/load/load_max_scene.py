import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.pipeline import (
    containerise, load_Openpype_data_max_raw
)
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
        load_Openpype_data_max_raw()
        path = self.filepath_from_context(context)
        path = os.path.normpath(path)
        # import the max scene by using "merge file"
        path = path.replace('\\', '/')
        rt.MergeMaxFile(path)

        max_container = rt.getLastMergedNodes()

        return containerise(
            name, max_container, context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.GetNodeByName(node_name)
        # delete the old container with attribute
        # delete old duplicate
        prev_max_objects = [obj for obj in rt.getLastMergedNodes()
                            if rt.ClassOf(obj) == rt.Container]
        for prev_object in prev_max_objects:
            rt.Delete(prev_object)
        rt.MergeMaxFile(path, rt.Name("deleteOldDups"))

        max_objects = rt.getLastMergedNodes()
        for max_object in max_objects:
            max_object.Parent = node

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
