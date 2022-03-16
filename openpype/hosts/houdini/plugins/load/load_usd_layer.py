from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import lib, pipeline


class USDSublayerLoader(load.LoaderPlugin):
    """Sublayer USD file in Solaris"""

    families = [
        "usd",
        "usdCamera",
    ]
    label = "Sublayer USD"
    representations = ["usd", "usda", "usdlc", "usdnc", "abc"]
    order = 1

    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import os
        import hou

        # Format file name, Houdini only wants forward slashes
        file_path = os.path.normpath(self.fname)
        file_path = file_path.replace("\\", "/")

        # Get the root node
        stage = hou.node("/stage")

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        # Create USD reference
        container = stage.createNode("sublayer", node_name=node_name)
        container.setParms({"filepath1": file_path})
        container.moveToGoodPosition()

        # Imprint it manually
        data = {
            "schema": "avalon-core:container-2.0",
            "id": pipeline.AVALON_CONTAINER_ID,
            "name": node_name,
            "namespace": namespace,
            "loader": str(self.__class__.__name__),
            "representation": str(context["representation"]["_id"]),
        }

        # todo: add folder="Avalon"
        lib.imprint(container, data)

        return container

    def update(self, container, representation):

        node = container["node"]

        # Update the file path
        file_path = get_representation_path(representation)
        file_path = file_path.replace("\\", "/")

        # Update attributes
        node.setParms(
            {
                "filepath1": file_path,
                "representation": str(representation["_id"]),
            }
        )

        # Reload files
        node.parm("reload").pressButton()

    def remove(self, container):

        node = container["node"]
        node.destroy()
