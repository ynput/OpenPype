import os
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import maintained_selection


class ObjLoader(load.LoaderPlugin):
    """Obj Loader"""

    families = ["model"]
    representations = ["obj"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.filepath_from_context(context))
        self.log.debug(f"Executing command to import..")

        rt.execute(f'importFile @"{filepath}" #noPrompt using:ObjImp')
        # create "missing" container for obj import
        container = rt.container()
        container.name = f"{name}"

        # get current selection
        for selection in rt.getCurrentSelection():
            selection.Parent = container

        asset = rt.getNodeByName(f"{name}")

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.getNodeByName(node_name)

        instance_name, _ = node_name.split("_")
        container = rt.getNodeByName(instance_name)
        for n in container.Children:
            rt.delete(n)

        rt.execute(f'importFile @"{path}" #noPrompt using:ObjImp')
        # get current selection
        for selection in rt.getCurrentSelection():
            selection.Parent = container

        with maintained_selection():
            rt.select(node)

        lib.imprint(node_name, {
            "representation": str(representation["_id"])
        })

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
