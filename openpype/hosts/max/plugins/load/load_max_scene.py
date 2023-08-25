import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    unique_namespace,
    get_namespace,
    object_transform_set
)
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
    postfix = "param"

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
        container_name = f"{namespace}:{name}_{self.postfix}"
        container = rt.Container(name=container_name)
        import_custom_attribute_data(container, max_objects)
        max_container.append(container)
        max_container.extend(max_objects)
        for max_obj, obj_name in zip(max_objects, max_object_names):
            max_obj.name = f"{namespace}:{obj_name}"
        return containerise(
            name, max_container, context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]

        node = rt.getNodeByName(node_name)
        namespace, name = get_namespace(node_name)
        sub_container_name = f"{namespace}:{name}_{self.postfix}"
        # delete the old container with attribute
        # delete old duplicate
        rt.Select(node.Children)
        transform_data = object_transform_set(node.Children)
        for prev_max_obj in rt.GetCurrentSelection():
            if rt.isValidNode(prev_max_obj) and prev_max_obj.name != sub_container_name:  # noqa
                rt.Delete(prev_max_obj)
        rt.MergeMaxFile(path, rt.Name("deleteOldDups"))

        current_max_objects = rt.getLastMergedNodes()
        current_max_object_names = [obj.name for obj
                                    in current_max_objects]
        sub_container = rt.getNodeByName(sub_container_name)
        update_custom_attribute_data(sub_container, current_max_objects)
        for max_object in current_max_objects:
            max_object.Parent = node
        for max_obj, obj_name in zip(current_max_objects,
                                     current_max_object_names):
            max_obj.name = f"{namespace}:{obj_name}"
            max_obj.pos = transform_data[
                f"{max_obj.name}.transform"]
            max_obj.scale = transform_data[
                f"{max_obj.name}.scale"]

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
