import os
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


class ObjLoader(load.LoaderPlugin):
    """Obj Loader"""

    families = ["model"]
    representations = ["obj"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.fname)
        self.log.debug(f"Executing command to import..")

        rt.execute(f'importFile @"{filepath}" #noPrompt using:ObjImp')
        # get current selection
        for selection in rt.getCurrentSelection():
            # create "missing" container for obj import
            container = rt.container()
            container.name = f"{name}"
            selection.Parent = container

        asset = rt.getNodeByName(f"{name}")

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])

        objects = self.get_container_children(node)
        for obj in objects:
            obj.source = path

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
