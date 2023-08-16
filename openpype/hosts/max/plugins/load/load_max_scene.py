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
        rt.MergeMaxFile(path, quiet=True, includeFullGroup=True)
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
        node = rt.getNodeByName(node_name)
        inst_name, _ = node_name.split("_")
        inst_container = rt.getNodeByName(inst_name)
        # delete the old container with attribute
        # delete old duplicate
        prev_max_object_names = [obj.name for obj
                                 in rt.getLastMergedNodes()]
        rt.MergeMaxFile(path, rt.Name("deleteOldDups"))

        current_max_objects = rt.getLastMergedNodes()
        current_max_object_names = [obj.name for obj
                                    in current_max_objects]
        for name in current_max_object_names:
            idx = rt.findItem(prev_max_object_names, name)
            if idx:
                prev_max_object_names = rt.deleteItem(prev_max_object_names, idx)
        for object_name in prev_max_object_names:
            prev_max_object = rt.getNodeByName(object_name)
            rt.Delete(prev_max_object)

        update_custom_attribute_data(inst_container, current_max_objects)

        for max_object in current_max_objects:
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
