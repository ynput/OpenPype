import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.pipeline import containerise
from openpype.pipeline import get_representation_path, load


class MaxSceneLoader(load.LoaderPlugin):
    """Max Scene Loader."""

    families = ["camera",
                "maxScene",
                "model"]

    representations = ["max"]
    order = -8
    icon = "code-fork"
    color = "green"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        path = self.filepath_from_context(context)
        path = os.path.normpath(path)
        # import the max scene by using "merge file"
        path = path.replace('\\', '/')
        rt.MergeMaxFile(
            path, rt.Name("mergeDups"),
            includeFullGroup=True)
        max_objects = rt.getLastMergedNodes()

        return containerise(
            name, [max_objects], context, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        prev_max_objects = rt.getLastMergedNodes()
        merged_max_objects = [obj.name for obj
                              in prev_max_objects]
        rt.MergeMaxFile(
            path, merged_max_objects,
            rt.Name("deleteOldDups"),
            quiet=True,
            mergedNodes=prev_max_objects,
            includeFullGroup=True)
        current_max_objects = rt.getLastMergedNodes()
        for current_object in current_max_objects:
            prev_max_objects = prev_max_objects.remove(current_object)
        for prev_object in prev_max_objects:
            rt.Delete(prev_object)

        lib.imprint(container["instance_node"], {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
