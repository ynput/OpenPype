import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import (
    containerise, import_custom_attribute_data,
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

        filepath = os.path.normpath(self.filepath_from_context(context))
        rt.FBXImporterSetParam("Animation", False)
        rt.FBXImporterSetParam("Cameras", False)
        rt.FBXImporterSetParam("Mode", rt.Name("create"))
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.importFile(filepath, rt.name("noPrompt"), using=rt.FBXIMP)

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        container = rt.container(name=f"{namespace}:{name}")
        selections = rt.GetCurrentSelection()
        import_custom_attribute_data(container, selections)

        for selection in selections:
            selection.Parent = container
            selection.name = f"{namespace}:{selection.name}"

        return containerise(
            name, [container], context,
            namespace, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        from pymxs import runtime as rt
        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.getNodeByName(node_name)
        namespace, name = get_namespace(node_name)
        sub_node_name = f"{namespace}:{name}"
        inst_container = rt.getNodeByName(sub_node_name)
        rt.Select(inst_container.Children)
        transform_data = object_transform_set(inst_container.Children)
        for prev_fbx_obj in rt.selection:
            if rt.isValidNode(prev_fbx_obj):
                rt.Delete(prev_fbx_obj)

        rt.FBXImporterSetParam("Animation", False)
        rt.FBXImporterSetParam("Cameras", False)
        rt.FBXImporterSetParam("Mode", rt.Name("merge"))
        rt.FBXImporterSetParam("AxisConversionMethod", True)
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.importFile(path, rt.name("noPrompt"), using=rt.FBXIMP)
        current_fbx_objects = rt.GetCurrentSelection()
        for fbx_object in current_fbx_objects:
            if fbx_object.Parent != inst_container:
                fbx_object.Parent = inst_container
                fbx_object.name = f"{namespace}:{fbx_object.name}"
                fbx_object.pos = transform_data[
                    f"{fbx_object.name}.transform"]
                fbx_object.rotation = transform_data[
                    f"{fbx_object.name}.rotation"]
                fbx_object.scale = transform_data[
                    f"{fbx_object.name}.scale"]

        for children in node.Children:
            if rt.classOf(children) == rt.Container:
                if children.name == sub_node_name:
                    update_custom_attribute_data(
                        children, current_fbx_objects)

        with maintained_selection():
            rt.Select(node)

        lib.imprint(
            node_name,
            {"representation": str(representation["_id"])},
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
