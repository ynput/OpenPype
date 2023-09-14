import os
from openpype.pipeline import load, get_representation_path
from openpype.pipeline.load import LoadError
from openpype.hosts.max.api.pipeline import (
    containerise,
    get_previous_loaded_object,
    update_custom_attribute_data
)

from openpype.hosts.max.api.lib import (
    unique_namespace,
    get_namespace,
    object_transform_set
)
from openpype.hosts.max.api import lib
from pymxs import runtime as rt


class OxAbcLoader(load.LoaderPlugin):
    """Ornatrix Alembic loader."""

    families = ["camera", "animation", "pointcache"]
    label = "Load Alembic with Ornatrix"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"
    postfix = "param"

    def load(self, context, name=None, namespace=None, data=None):
        plugin_list = get_plugins()
        if "ephere.plugins.autodesk.max.ornatrix.dlo" not in plugin_list:
            raise LoadError("Ornatrix plugin not "
                            "found/installed in Max yet..")

        file_path = os.path.normpath(self.filepath_from_context(context))
        rt.AlembicImport.ImportToRoot = True
        rt.AlembicImport.CustomAttributes = True
        rt.importFile(
            file_path, rt.name("noPrompt"),
            using=rt.Ornatrix_Alembic_Importer)

        scene_object = []
        for obj in rt.rootNode.Children:
            obj_type = rt.ClassOf(obj)
            if str(obj_type).startswith("Ox_"):
                scene_object.append(obj)

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        abc_container = []
        for abc in scene_object:
            abc.name = f"{namespace}:{abc.name}"
            abc_container.append(abc)

        return containerise(
            name, abc_container, context,
            namespace, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        path = get_representation_path(representation)
        node_name = container["instance_node"]
        namespace, name = get_namespace(node_name)
        node = rt.getNodeByName(node_name)
        node_list = get_previous_loaded_object(node)
        rt.Select(node_list)
        selections = rt.getCurrentSelection()
        transform_data = object_transform_set(selections)
        for prev_obj in selections:
            if rt.isValidNode(prev_obj):
                rt.Delete(prev_obj)

        rt.AlembicImport.ImportToRoot = False
        rt.AlembicImport.CustomAttributes = True
        rt.importFile(
            path, rt.name("noPrompt"),
            using=rt.Ornatrix_Alembic_Importer)

        scene_object = []
        for obj in rt.rootNode.Children:
            obj_type = rt.ClassOf(obj)
            if str(obj_type).startswith("Ox_"):
                scene_object.append(obj)
        ox_abc_objects = []
        for abc in scene_object:
            abc.Parent = container
            abc.name = f"{namespace}:{abc.name}"
            ox_abc_objects.append(abc)
            ox_transform = f"{abc.name}.transform"
            if ox_transform in transform_data.keys():
                abc.pos = transform_data[ox_transform] or 0
                abc.scale = transform_data[f"{abc.name}.scale"] or 0
        update_custom_attribute_data(node, ox_abc_objects)
        lib.imprint(
            container["instance_node"],
            {"representation": str(representation["_id"])},
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)


def get_plugins() -> list:
    """Get plugin list from 3ds max."""
    manager = rt.PluginManager
    count = manager.pluginDllCount
    plugin_info_list = []
    for p in range(1, count + 1):
        plugin_info = manager.pluginDllName(p)
        plugin_info_list.append(plugin_info)

    return plugin_info_list
