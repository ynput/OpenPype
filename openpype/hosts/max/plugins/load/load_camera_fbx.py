import os

from openpype.hosts.max.api import lib, maintained_selection
from openpype.hosts.max.api.lib import unique_namespace
from openpype.hosts.max.api.pipeline import (
    containerise,
    import_custom_attribute_data,
    update_custom_attribute_data
)
from openpype.pipeline import get_representation_path, load


class FbxLoader(load.LoaderPlugin):
    """Fbx Loader."""

    families = ["camera"]
    representations = ["fbx"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt
        filepath = self.filepath_from_context(context)
        filepath = os.path.normpath(filepath)
        rt.FBXImporterSetParam("Animation", True)
        rt.FBXImporterSetParam("Camera", True)
        rt.FBXImporterSetParam("AxisConversionMethod", True)
        rt.FBXImporterSetParam("Mode", rt.Name("create"))
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.ImportFile(
            filepath,
            rt.name("noPrompt"),
            using=rt.FBXIMP)

        container = rt.container(name=name)
        selections = rt.GetCurrentSelection()
        import_custom_attribute_data(container, selections)
        for selection in selections:
            selection.Parent = container

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )

        return containerise(
            name, [container], context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.getNodeByName(node_name)
        container_name = node_name.split(":")[-1]
        param_container, _ = container_name.split("_")

        inst_container = rt.getNodeByName(param_container)
        rt.Select(node.Children)

        rt.FBXImporterSetParam("Animation", True)
        rt.FBXImporterSetParam("Camera", True)
        rt.FBXImporterSetParam("Mode", rt.Name("merge"))
        rt.FBXImporterSetParam("AxisConversionMethod", True)
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.ImportFile(
            path, rt.name("noPrompt"), using=rt.FBXIMP)
        current_fbx_objects = rt.GetCurrentSelection()
        for fbx_object in current_fbx_objects:
            if fbx_object.Parent != inst_container:
                fbx_object.Parent = inst_container

        for children in node.Children:
            if rt.classOf(children) == rt.Container:
                if children.name == param_container:
                    update_custom_attribute_data(
                        children, current_fbx_objects)

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
