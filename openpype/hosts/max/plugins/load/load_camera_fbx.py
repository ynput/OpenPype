import os

from openpype.hosts.max.api import lib, maintained_selection
from openpype.hosts.max.api.pipeline import containerise
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

        filepath = os.path.normpath(self.fname)
        rt.FBXImporterSetParam("Animation", True)
        rt.FBXImporterSetParam("Camera", True)
        rt.FBXImporterSetParam("AxisConversionMethod", True)
        rt.FBXImporterSetParam("Preserveinstances", True)
        rt.ImportFile(
            filepath,
            rt.name("noPrompt"),
            using=rt.FBXIMP)

        container = rt.GetNodeByName(f"{name}")
        if not container:
            container = rt.Container()
            container.name = f"{name}"

        for selection in rt.GetCurrentSelection():
            selection.Parent = container

        return containerise(
            name, [container], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.GetNodeByName(container["instance_node"])
        rt.Select(node.Children)
        fbx_reimport_cmd = (
            f"""

FBXImporterSetParam "Animation" true
FBXImporterSetParam "Cameras" true
FBXImporterSetParam "AxisConversionMethod" true
FbxExporterSetParam "UpAxis" "Y"
FbxExporterSetParam "Preserveinstances" true

importFile @"{path}" #noPrompt using:FBXIMP
        """)
        rt.Execute(fbx_reimport_cmd)

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
