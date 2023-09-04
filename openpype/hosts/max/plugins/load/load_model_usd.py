import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    unique_namespace,
    get_namespace,
    object_transform_set
)
from openpype.hosts.max.api.lib import maintained_selection
from openpype.hosts.max.api.pipeline import (
    containerise,
    import_custom_attribute_data
)
from openpype.pipeline import get_representation_path, load


class ModelUSDLoader(load.LoaderPlugin):
    """Loading model with the USD loader."""

    families = ["model"]
    label = "Load Model(USD)"
    representations = ["usda"]
    order = -10
    icon = "code-fork"
    color = "orange"
    postfix = "param"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        # asset_filepath
        filepath = os.path.normpath(self.filepath_from_context(context))
        import_options = rt.USDImporter.CreateOptions()
        base_filename = os.path.basename(filepath)
        filename, ext = os.path.splitext(base_filename)
        log_filepath = filepath.replace(ext, "txt")

        rt.LogPath = log_filepath
        rt.LogLevel = rt.Name("info")
        rt.USDImporter.importFile(filepath,
                                  importOptions=import_options)
        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        asset = rt.GetNodeByName(name)
        import_custom_attribute_data(asset, asset.Children)
        for usd_asset in asset.Children:
            usd_asset.name = f"{namespace}:{usd_asset.name}"

        asset_name = f"{namespace}:{name}_{self.postfix}"
        asset.name = asset_name
        # need to get the correct container after renamed
        asset = rt.GetNodeByName(asset_name)


        return containerise(
            name, [asset], context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.GetNodeByName(node_name)
        namespace, name = get_namespace(node_name)
        sub_node_name = f"{namespace}:{name}_{self.postfix}"
        transform_data = None
        for n in node.Children:
            rt.Select(n.Children)
            transform_data = object_transform_set(n.Children)
            for prev_usd_asset in rt.selection:
                if rt.isValidNode(prev_usd_asset):
                    rt.Delete(prev_usd_asset)
            rt.Delete(n)

        import_options = rt.USDImporter.CreateOptions()
        base_filename = os.path.basename(path)
        _, ext = os.path.splitext(base_filename)
        log_filepath = path.replace(ext, "txt")

        rt.LogPath = log_filepath
        rt.LogLevel = rt.Name("info")
        rt.USDImporter.importFile(
            path, importOptions=import_options)

        asset = rt.GetNodeByName(name)
        asset.Parent = node
        import_custom_attribute_data(asset, asset.Children)
        for children in asset.Children:
            children.name = f"{namespace}:{children.name}"
            children.pos = transform_data[
                f"{children.name}.transform"]
            children.scale = transform_data[
                f"{children.name}.scale"]

        asset.name = sub_node_name

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
