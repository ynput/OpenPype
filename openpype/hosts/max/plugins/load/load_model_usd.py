import os
from openpype.pipeline import (
    load, get_representation_path
)
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


class ModelUSDLoader(load.LoaderPlugin):
    """Loading model with the USD loader."""

    families = ["model"]
    label = "Load Model(USD)"
    representations = ["usda"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt
        # asset_filepath
        filepath = os.path.normpath(self.fname)
        import_options = rt.USDImporter.CreateOptions()
        base_filename = os.path.basename(filepath)
        filename, ext = os.path.splitext(base_filename)
        log_filepath = filepath.replace(ext, "txt")

        rt.LogPath = log_filepath
        rt.LogLevel = rt.name('info')
        rt.USDImporter.importFile(filepath,
                                  importOptions=import_options)

        asset = rt.getNodeByName(f"{name}")

        return containerise(
            name, [asset], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])

        usd_objects = node.Children
        for usd_object in usd_objects:
            usd_object.source = path

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)
