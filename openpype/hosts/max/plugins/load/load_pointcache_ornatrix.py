import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


class OxAbcLoader(load.LoaderPlugin):
    """Ornatrix Alembic loader."""

    families = ["camera", "animation", "pointcache"]
    label = "Load Alembic with Ornatrix"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        file_path = os.path.normpath(self.filepath_from_context(context))
        scene_object_before = [obj for obj in rt.rootNode.Children]
        rt.AlembicImport.ImportToRoot = True
        rt.AlembicImport.CustomAttributes = True
        rt.importFile(file_path)
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
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        instance_name, _ = os.path.splitext(node_name)
        container = rt.getNodeByName(instance_name)
        for children in container.Children:
            rt.Delete(children)

        scene_object_before = [obj for obj in rt.rootNode.Children]
        rt.AlembicImport.ImportToRoot = False
        rt.AlembicImport.CustomAttributes = True
        rt.importFile(path)
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
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
