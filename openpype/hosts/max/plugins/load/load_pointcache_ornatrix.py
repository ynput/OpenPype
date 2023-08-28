import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import containerise
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

    def load(self, context, name=None, namespace=None, data=None):
        plugin_list = get_plugins()
        if "ornatrix.dlo" not in plugin_list:
            raise RuntimeError("Ornatrix plugin not "
                               "found/installed in Max yet..")

        file_path = os.path.normpath(self.filepath_from_context(context))
        scene_object_before = [obj for obj in rt.rootNode.Children]
        rt.AlembicImport.ImportToRoot = True
        rt.AlembicImport.CustomAttributes = True
        rt.importFile(
            file_path, rt.name("noPrompt"),
            using=rt.Ornatrix_Alembic_Importer)
        scene_object_after = [obj for obj in rt.rootNode.Children]
        for scene_object in scene_object_before:
            scene_object_after = scene_object_after.remove(scene_object)

        abc_container = rt.Container(name=name)
        for abc in scene_object_after:
            abc.Parent = abc_container

        return containerise(
            name, [abc_container], context, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        path = get_representation_path(representation)
        node_name = container["instance_node"]
        instance_name, _ = os.path.splitext(node_name)
        container = rt.getNodeByName(instance_name)
        for children in container.Children:
            rt.Delete(children)

        scene_object_before = [obj for obj in rt.rootNode.Children]
        rt.AlembicImport.ImportToRoot = False
        rt.AlembicImport.CustomAttributes = True
        rt.importFile(
            path, rt.name("noPrompt"),
            using=rt.Ornatrix_Alembic_Importer)
        scene_object_after = [obj for obj in rt.rootNode.Children]
        for scene_object in scene_object_before:
            scene_object_after = scene_object_after.remove(scene_object)

        for scene_object in scene_object_after:
            scene_object.Parent = container

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
