# -*- coding: utf-8 -*-
"""Fbx Loader for houdini.

It's almost a copy of
'load_bgeo.py'and 'load_alembic.py'
however this one includes extra comments for demonstration.

This plugin is part of publish process guide.
"""
import os

from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import pipeline


class FbxLoader(load.LoaderPlugin):
    """Load fbx files to Houdini."""

    label = "Load FBX"
    families = ["staticMesh", "fbx"]
    representations = ["fbx"]

    # Usually you will use these value as default
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        # get file path
        file_path = self.get_file_path(context)

        # get necessary data
        namespace, node_name = self.get_node_name(context, name, namespace)

        # create load tree
        nodes = self.create_load_node_tree(file_path, node_name, name)

        self[:] = nodes

        # Call containerise function which does some
        # automations for you
        containerised_nodes = self.get_containerised_nodes(
            nodes, context, node_name, namespace
        )

        return containerised_nodes

    def update(self, container, representation):

        node = container["node"]
        try:
            file_node = next(
                n for n in node.children() if n.type().name() == "file"
            )
        except StopIteration:
            self.log.error("Could not find node of type `file`")
            return

        # Update the file path
        file_path = get_representation_path(representation)
        file_path = self.format_path(file_path, representation)

        file_node.setParms({"file": file_path})

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()

    def switch(self, container, representation):
        self.update(container, representation)

    def get_file_path(self, context):
        """Return formatted file path."""

        # Format file name, Houdini only wants forward slashes
        file_path = self.filepath_from_context(context)
        file_path = os.path.normpath(file_path)
        file_path = file_path.replace("\\", "/")

        return file_path

    def get_node_name(self, context, name=None, namespace=None):
        """Define node name."""

        if not namespace:
            namespace = context["asset"]["name"]

        if namespace:
            node_name = "{}_{}".format(namespace, name)
        else:
            node_name = name

        return namespace, node_name

    def create_load_node_tree(self, file_path, node_name, subset_name):
        """Create Load network.

        you can start building your tree at any obj level.
        it'll be much easier to build it in the root obj level.

        Afterwards, your tree will be automatically moved to
        '/obj/AVALON_CONTAINERS' subnetwork.
        """
        import hou

        # Get the root obj level
        obj = hou.node("/obj")

        # Create a new obj geo node
        parent_node = obj.createNode("geo", node_name=node_name)

        # In older houdini,
        # when reating a new obj geo node, a default file node will be
        # automatically created.
        # so, we will delete it if exists.
        file_node = parent_node.node("file1")
        if file_node:
            file_node.destroy()

        # Create a new file node
        file_node = parent_node.createNode("file", node_name=node_name)
        file_node.setParms({"file": file_path})

        # Create attribute delete
        attribdelete_name = "attribdelete_{}".format(subset_name)
        attribdelete = parent_node.createNode("attribdelete",
                                              node_name=attribdelete_name)
        attribdelete.setParms({"ptdel": "fbx_*"})
        attribdelete.setInput(0, file_node)

        # Create a Null node
        null_name = "OUT_{}".format(subset_name)
        null = parent_node.createNode("null", node_name=null_name)
        null.setInput(0, attribdelete)

        # Ensure display flag is on the file_node input node and not on the OUT
        # node to optimize "debug" displaying in the viewport.
        file_node.setDisplayFlag(True)

        # Set new position for unpack node else it gets cluttered
        nodes = [parent_node, file_node, attribdelete, null]
        for nr, node in enumerate(nodes):
            node.setPosition([0, (0 - nr)])

        return nodes

    def get_containerised_nodes(self, nodes, context, node_name, namespace):
        """Call containerise function.

        It does some automations that you don't have to worry about, e.g.
            1. It moves created nodes to the AVALON_CONTAINERS  subnetwork
            2. Add extra parameters
        """
        containerised_nodes = pipeline.containerise(
            node_name,
            namespace,
            nodes,
            context,
            self.__class__.__name__,
            suffix="",
        )

        return containerised_nodes
