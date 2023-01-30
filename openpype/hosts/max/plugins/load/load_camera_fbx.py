import os
from openpype.pipeline import (
    load
)


class FbxLoader(load.LoaderPlugin):
    """Fbx Loader"""

    families = ["camera"]
    representations = ["fbx"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.fname)

        fbx_import_cmd = (
            f"""

FBXImporterSetParam "Animation" true
FBXImporterSetParam "Cameras" true
FBXImporterSetParam "AxisConversionMethod" true
FbxExporterSetParam "UpAxis" "Y"
FbxExporterSetParam "Preserveinstances" true

importFile @"{filepath}" #noPrompt using:FBXIMP
        """)

        self.log.debug(f"Executing command: {fbx_import_cmd}")
        rt.execute(fbx_import_cmd)

        container_name = f"{name}_CON"

        asset = rt.getNodeByName(f"{name}")
        # rename the container with "_CON"
        container = rt.container(name=container_name)
        asset.Parent = container

        return container

    def remove(self, container):
        from pymxs import runtime as rt

        node = container["node"]
        rt.delete(node)
