import os
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


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

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])

        fbx_objects = self.get_container_children(node)
        for fbx_object in fbx_objects:
            fbx_object.source = path

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
