import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import (
    containerise, get_previous_loaded_object,
    update_custom_attribute_data
)
from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    unique_namespace,
    get_namespace,
    object_transform_set
)
from openpype.hosts.max.api.lib import maintained_selection


class FbxModelLoader(load.LoaderPlugin):
    """Fbx Model Loader."""

    families = ["model"]
    representations = ["fbx"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt
        filepath = self.filepath_from_context(context)
        filepath = os.path.normpath(filepath)
        rt.FBXImporterSetParam("Animation", False)
        rt.FBXImporterSetParam("Cameras", False)
        rt.FBXImporterSetParam("Mode", rt.Name("create"))
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.importFile(
            filepath, rt.name("noPrompt"), using=rt.FBXIMP)

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        selections = rt.GetCurrentSelection()

        for selection in selections:
            selection.name = f"{namespace}:{selection.name}"

        return containerise(
            name, selections, context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.getNodeByName(node_name)
        namespace, _ = get_namespace(node_name)

        node_list = get_previous_loaded_object(node)
        rt.Select(node_list)
        prev_fbx_objects = rt.GetCurrentSelection()
        transform_data = object_transform_set(prev_fbx_objects)
        for prev_fbx_obj in prev_fbx_objects:
            if rt.isValidNode(prev_fbx_obj):
                rt.Delete(prev_fbx_obj)

        rt.FBXImporterSetParam("Animation", False)
        rt.FBXImporterSetParam("Cameras", False)
        rt.FBXImporterSetParam("Mode", rt.Name("create"))
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.importFile(path, rt.name("noPrompt"), using=rt.FBXIMP)
        current_fbx_objects = rt.GetCurrentSelection()
        update_custom_attribute_data(node, current_fbx_objects)
        for fbx_object in current_fbx_objects:
            fbx_object.name = f"{namespace}:{fbx_object.name}"
            if fbx_object in node_list:
                fbx_object.pos = transform_data[
                    f"{fbx_object.name}.transform"] or 0
                fbx_object.scale = transform_data[
                    f"{fbx_object.name}.scale"] or 0

        with maintained_selection():
            rt.Select(node)

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
