# -*- coding: utf-8 -*-
"""Simple alembic loader for 3dsmax.

Because of limited api, alembics can be only loaded, but not easily updated.

"""
import os
from openpype.pipeline import (
    load
)


class AbcLoader(load.LoaderPlugin):
    """Alembic loader."""

    families = ["model", "animation", "pointcache"]
    label = "Load Alembic"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        file_path = os.path.normpath(self.fname)

        abc_before = {
            c for c in rt.rootNode.Children
            if rt.classOf(c) == rt.AlembicContainer
        }

        abc_export_cmd = (f"""
AlembicImport.ImportToRoot = false

importFile @"{file_path}" #noPrompt
        """)

        self.log.debug(f"Executing command: {abc_export_cmd}")
        rt.execute(abc_export_cmd)

        abc_after = {
            c for c in rt.rootNode.Children
            if rt.classOf(c) == rt.AlembicContainer
        }

        # This should yield new AlembicContainer node
        abc_containers = abc_after.difference(abc_before)

        if len(abc_containers) != 1:
            self.log.error("Something failed when loading.")

        abc_container = abc_containers.pop()

        container_name = f"{name}_CON"
        container = rt.container(name=container_name)
        abc_container.Parent = container

        return container

    def remove(self, container):
        from pymxs import runtime as rt

        node = container["node"]
        rt.delete(node)
