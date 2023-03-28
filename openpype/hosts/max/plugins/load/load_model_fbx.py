import os
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import maintained_selection


class FbxModelLoader(load.LoaderPlugin):
    """Fbx Model Loader"""

    families = ["model"]
    representations = ["fbx"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.fname)

        fbx_import_cmd = (
            f"""

FBXImporterSetParam "Animation" false
FBXImporterSetParam "Cameras" false
FBXImporterSetParam "AxisConversionMethod" true
FbxExporterSetParam "UpAxis" "Y"
FbxExporterSetParam "Preserveinstances" true

importFile @"{filepath}" #noPrompt using:FBXIMP
        """)

        self.log.debug(f"Executing command: {fbx_import_cmd}")
        rt.execute(fbx_import_cmd)

        asset = rt.getNodeByName(f"{name}")

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])
        rt.select(node.Children)
        fbx_reimport_cmd = (
            f"""
FBXImporterSetParam "Animation" false
FBXImporterSetParam "Cameras" false
FBXImporterSetParam "AxisConversionMethod" true
FbxExporterSetParam "UpAxis" "Y"
FbxExporterSetParam "Preserveinstances" true

importFile @"{path}" #noPrompt using:FBXIMP
        """)
        rt.execute(fbx_reimport_cmd)

        with maintained_selection():
            rt.select(node)

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
