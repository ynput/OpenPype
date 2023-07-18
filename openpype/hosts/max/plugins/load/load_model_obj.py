import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import maintained_selection
from openpype.hosts.max.api.pipeline import containerise
from openpype.pipeline import get_representation_path, load


class ObjLoader(load.LoaderPlugin):
    """Obj Loader."""

    families = ["model"]
    representations = ["obj"]
    order = -9
    icon = "code-fork"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.filepath_from_context(context))
        self.log.debug("Executing command to import..")

        rt.Execute(f'importFile @"{filepath}" #noPrompt using:ObjImp')
        # create "missing" container for obj import
        container = rt.Container()
        container.name = name

        # get current selection
        for selection in rt.GetCurrentSelection():
            selection.Parent = container

        asset = rt.GetNodeByName(name)

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.GetNodeByName(node_name)

        instance_name, _ = node_name.split("_")
        container = rt.GetNodeByName(instance_name)
        for child in container.Children:
            rt.Delete(child)

        rt.Execute(f'importFile @"{path}" #noPrompt using:ObjImp')
        # get current selection
        for selection in rt.GetCurrentSelection():
            selection.Parent = container

        with maintained_selection():
            rt.Select(node)

        lib.imprint(node_name, {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
