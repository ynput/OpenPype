import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import containerise
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

        filepath = os.path.normpath(self.fname)
        rt.FBXImporterSetParam("Animation", False)
        rt.FBXImporterSetParam("Cameras", False)
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.importFile(filepath, rt.name("noPrompt"), using=rt.FBXIMP)

        container = rt.GetNodeByName(name)
        if not container:
            container = rt.Container()
            container.name = name

        for selection in rt.GetCurrentSelection():
            selection.Parent = container

        return containerise(
            name, [container], context, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        from pymxs import runtime as rt
        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])
        rt.select(node.Children)

        rt.FBXImporterSetParam("Animation", False)
        rt.FBXImporterSetParam("Cameras", False)
        rt.FBXImporterSetParam("AxisConversionMethod", True)
        rt.FBXImporterSetParam("UpAxis", "Y")
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.importFile(path, rt.name("noPrompt"), using=rt.FBXIMP)

        with maintained_selection():
            rt.Select(node)

        lib.imprint(
            container["instance_node"],
            {"representation": str(representation["_id"])},
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
