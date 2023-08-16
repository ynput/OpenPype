import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import (
    containerise, import_custom_attribute_data, update_custom_attribute_data
)
from openpype.hosts.max.api import lib
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

        container = rt.GetNodeByName(name)

        container = rt.Container(name=name)

        selections = rt.GetCurrentSelection()
        import_custom_attribute_data(container, selections)

        for selection in selections:
            selection.Parent = container

        return containerise(
            name, [container], context, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        from pymxs import runtime as rt
        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.getNodeByName(node_name)
        inst_name, _ = node_name.split("_")
        inst_container = rt.getNodeByName(inst_name)

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
        update_custom_attribute_data(
            inst_container, current_fbx_objects)
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
