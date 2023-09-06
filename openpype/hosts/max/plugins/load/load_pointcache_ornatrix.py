import os
from openpype.pipeline import load, get_representation_path
from openpype.pipeline.load import LoaderError
from openpype.hosts.max.api.pipeline import (
    containerise,
    import_custom_attribute_data,
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
            raise LoaderError("Ornatrix plugin not "
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

        abc_container = rt.Container()
        for abc in scene_object:
            abc.Parent = abc_container
            abc.name = f"{namespace}:{abc.name}"
        # rename the abc container with namespace
        abc_container_name = f"{namespace}:{name}_{self.postfix}"
        abc_container.name = abc_container_name
        import_custom_attribute_data(
            abc_container, abc_container.Children)

        return containerise(
            name, [abc_container], context,
            namespace, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        path = get_representation_path(representation)
        node_name = container["instance_node"]
        namespace, name = get_namespace(node_name)
        sub_node_name = f"{namespace}:{name}_{self.postfix}"
        inst_container = rt.getNodeByName(sub_node_name)
        rt.Select(inst_container.Children)
        transform_data = object_transform_set(inst_container.Children)
        for prev_obj in rt.selection:
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
        update_custom_attribute_data(
            inst_container, scene_object.Children)
        for abc in scene_object:
            abc.Parent = container
            abc.name = f"{namespace}:{abc.name}"
            abc.pos = transform_data[f"{abc.name}.transform"]
            abc.scale = transform_data[f"{abc.name}.scale"]

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
