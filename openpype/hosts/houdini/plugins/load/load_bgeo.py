# -*- coding: utf-8 -*-
import os
import re

from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import pipeline


class BgeoLoader(load.LoaderPlugin):
    """Load bgeo files to Houdini."""

    label = "Load bgeo"
    families = ["model", "pointcache", "bgeo"]
    representations = [
        "bgeo", "bgeosc", "bgeogz",
        "bgeo.sc", "bgeo.gz", "bgeo.lzma", "bgeo.bz2"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import hou

        # Get the root node
        obj = hou.node("/obj")

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        # Create a new geo node
        container = obj.createNode("geo", node_name=node_name)
        is_sequence = bool(context["representation"]["context"].get("frame"))

        # Remove the file node, it only loads static meshes
        # Houdini 17 has removed the file node from the geo node
        file_node = container.node("file1")
        if file_node:
            file_node.destroy()

        # Explicitly create a file node
        file_node = container.createNode("file", node_name=node_name)
        file_node.setParms({"file": self.format_path(self.fname, is_sequence)})

        # Set display on last node
        file_node.setDisplayFlag(True)

        nodes = [container, file_node]
        self[:] = nodes

        return pipeline.containerise(
            node_name,
            namespace,
            nodes,
            context,
            self.__class__.__name__,
            suffix="",
        )

    @staticmethod
    def format_path(path, is_sequence):
        """Format file path correctly for single bgeo or bgeo sequence."""
        if not os.path.exists(path):
            raise RuntimeError("Path does not exist: %s" % path)

        # The path is either a single file or sequence in a folder.
        if not is_sequence:
            filename = path
            print("single")
        else:
            filename = re.sub(r"(.*)\.(\d+)\.(bgeo.*)", "\\1.$F4.\\3", path)

            filename = os.path.join(path, filename)

        filename = os.path.normpath(filename)
        filename = filename.replace("\\", "/")

        return filename

    def update(self, container, representation):

        node = container["node"]
        try:
            file_node = next(
                n for n in node.children() if n.type().name() == "file"
            )
        except StopIteration:
            self.log.error("Could not find node of type `alembic`")
            return

        # Update the file path
        file_path = get_representation_path(representation)
        file_path = self.format_path(file_path)

        file_node.setParms({"fileName": file_path})

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()
