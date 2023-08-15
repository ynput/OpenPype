import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.pipeline import (
    containerise, import_custom_attribute_data,
    update_custom_attribute_data
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
        path = self.filepath_from_context(context)
        path = os.path.normpath(path)
        # import the max scene by using "merge file"
        path = path.replace('\\', '/')
        rt.MergeMaxFile(path)
        max_objects = rt.getLastMergedNodes()
        # implement the OP/AYON custom attributes before load
        max_container = []
        container = rt.Container(name=name)
        import_custom_attribute_data(container, max_objects)
        max_container.append(container)
        max_container.extend(max_objects)
        return containerise(
            name, max_container, context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.GetNodeByName(node_name)
        inst_name, _ = os.path.splitext(node_name)
        old_container = rt.getNodeByName(inst_name)
        # delete the old container with attribute
        # delete old duplicate
        rt.Delete(old_container)
        rt.MergeMaxFile(path, rt.Name("deleteOldDups"))
        new_container = rt.Container(name=inst_name)
        max_objects = rt.getLastMergedNodes()

        max_objects_list = []
        max_objects_list.append(new_container)
        max_objects_list.extend(max_objects)

        for max_object in max_objects_list:
            max_object.Parent = node
        update_custom_attribute_data(new_container, max_objects)
        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
