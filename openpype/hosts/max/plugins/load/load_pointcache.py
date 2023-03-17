# -*- coding: utf-8 -*-
"""Simple alembic loader for 3dsmax.

Because of limited api, alembics can be only loaded, but not easily updated.

"""
import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import containerise
from openpype.hosts.max.api import lib


class AbcLoader(load.LoaderPlugin):
    """Alembic loader."""

    families = ["camera", "animation", "pointcache"]
    label = "Load Alembic"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        file_path = self.filepath_from_context(context)
        file_path = os.path.normpath(file_path)

        abc_before = {
            c
            for c in rt.rootNode.Children
            if rt.classOf(c) == rt.AlembicContainer
        }

        rt.AlembicImport.ImportToRoot = False
        rt.importFile(file_path, rt.name("noPrompt"))

        abc_after = {
            c
            for c in rt.rootNode.Children
            if rt.classOf(c) == rt.AlembicContainer
        }

        # This should yield new AlembicContainer node
        abc_containers = abc_after.difference(abc_before)

        if len(abc_containers) != 1:
            self.log.error("Something failed when loading.")

        abc_container = abc_containers.pop()

        return containerise(
            name, [abc_container], context, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.getNodeByName(container["instance_node"])

        alembic_objects = self.get_container_children(node, "AlembicObject")
        for alembic_object in alembic_objects:
            alembic_object.source = path

        lib.imprint(
            container["instance_node"],
            {"representation": str(representation["_id"])},
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.getNodeByName(container["instance_node"])
        rt.delete(node)

    @staticmethod
    def get_container_children(parent, type_name):
        from pymxs import runtime as rt

        def list_children(node):
            children = []
            for c in node.Children:
                children.append(c)
                children += list_children(c)
            return children

        filtered = []
        for child in list_children(parent):
            class_type = str(rt.classOf(child.baseObject))
            if class_type == type_name:
                filtered.append(child)

        return filtered
