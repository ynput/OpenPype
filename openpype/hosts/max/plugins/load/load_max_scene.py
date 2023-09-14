import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    unique_namespace,
    get_namespace,
    object_transform_set
)
from openpype.hosts.max.api.pipeline import (
    containerise, get_previous_loaded_object,
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
        max_object_names = [obj.name for obj in max_objects]
        # implement the OP/AYON custom attributes before load
        max_container = []
        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        for max_obj, obj_name in zip(max_objects, max_object_names):
            max_obj.name = f"{namespace}:{obj_name}"
            max_container.append(rt.getNodeByName(max_obj.name))
        return containerise(
            name, max_container, context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        print(node_name)
        node = rt.getNodeByName(node_name)
        namespace, _ = get_namespace(node_name)
        # delete the old container with attribute
        # delete old duplicate
        # use the modifier OP data to delete the data
        node_list = get_previous_loaded_object(node)
        rt.select(node_list)
        prev_max_objects = rt.GetCurrentSelection()
        print(f"{node_list}")
        transform_data = object_transform_set(prev_max_objects)

        for prev_max_obj in prev_max_objects:
            if rt.isValidNode(prev_max_obj):  # noqa
                rt.Delete(prev_max_obj)
        rt.MergeMaxFile(path, quiet=True)

        current_max_objects = rt.getLastMergedNodes()

        current_max_object_names = [obj.name for obj
                                    in current_max_objects]

        max_objects = []
        for max_obj, obj_name in zip(current_max_objects,
                                    current_max_object_names):
            max_obj.name = f"{namespace}:{obj_name}"
            max_objects.append(max_obj)
            max_transform = f"{max_obj.name}.transform"
            if max_transform in transform_data.keys():
                max_obj.pos = transform_data[max_transform] or 0
                max_obj.scale = transform_data[
                    f"{max_obj.name}.scale"] or 0

        update_custom_attribute_data(node, max_objects)
        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
