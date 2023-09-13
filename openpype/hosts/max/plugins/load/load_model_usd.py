import os

from pymxs import runtime as rt

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    unique_namespace,
    get_namespace,
    object_transform_set
)
from openpype.hosts.max.api.lib import maintained_selection
from openpype.hosts.max.api.pipeline import (
    containerise,
    get_previous_loaded_object,
    update_custom_attribute_data
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

    def load(self, context, name=None, namespace=None, data=None):
        # asset_filepath
        filepath = os.path.normpath(self.filepath_from_context(context))
        import_options = rt.USDImporter.CreateOptions()
        base_filename = os.path.basename(filepath)
        _, ext = os.path.splitext(base_filename)
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
        usd_objects = []

        for usd_asset in asset.Children:
            usd_asset.name = f"{namespace}:{usd_asset.name}"
            usd_objects.append(usd_asset)

        asset_name = f"{namespace}:{name}"
        asset.name = asset_name
        # need to get the correct container after renamed
        asset = rt.GetNodeByName(asset_name)
        usd_objects.append(asset)

        return containerise(
            name, usd_objects, context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.GetNodeByName(node_name)
        namespace, name = get_namespace(node_name)
        node_list = get_previous_loaded_object(node)
        rt.Select(node_list)
        prev_objects = rt.GetCurrentSelection()
        transform_data = object_transform_set(prev_objects)
        for n in prev_objects:
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
        usd_objects = []
        for children in asset.Children:
            children.name = f"{namespace}:{children.name}"
            usd_objects.append(children)
            if children in node_list:
                children.pos = transform_data[
                    f"{children.name}.transform"] or children.pos
                children.scale = transform_data[
                    f"{children.name}.scale"] or children.scale

        asset.name = f"{namespace}:{asset.name}"
        usd_objects.append(asset)
        update_custom_attribute_data(node, usd_objects)
        with maintained_selection():
            rt.Select(node)

        lib.imprint(node_name, {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
