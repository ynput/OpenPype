import os
import re

from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import pipeline


class VdbLoader(load.LoaderPlugin):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["vdbcache"]
    label = "Load VDB"
    representations = ["vdb"]
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

        # Remove the file node, it only loads static meshes
        # Houdini 17 has removed the file node from the geo node
        file_node = container.node("file1")
        if file_node:
            file_node.destroy()

        # Explicitly create a file node
        file_node = container.createNode("file", node_name=node_name)
        file_node.setParms({"file": self.format_path(self.fname)})

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

    def format_path(self, path):
        """Format file path correctly for single vdb or vdb sequence."""
        if not os.path.exists(path):
            raise RuntimeError("Path does not exist: %s" % path)

        # The path is either a single file or sequence in a folder.
        is_single_file = os.path.isfile(path)
        if is_single_file:
            filename = path
        else:
            # The path points to the publish .vdb sequence folder so we
            # find the first file in there that ends with .vdb
            files = sorted(os.listdir(path))
            first = next((x for x in files if x.endswith(".vdb")), None)
            if first is None:
                raise RuntimeError(
                    "Couldn't find first .vdb file of "
                    "sequence in: %s" % path
                )

            # Set <frame>.vdb to $F.vdb
            first = re.sub(r"\.(\d+)\.vdb$", ".$F.vdb", first)

            filename = os.path.join(path, first)

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
