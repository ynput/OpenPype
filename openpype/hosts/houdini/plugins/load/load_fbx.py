# -*- coding: utf-8 -*-
"""Fbx Loader for houdini. """
from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import pipeline


class FbxLoader(load.LoaderPlugin):
    """Load fbx files. """

    label = "Load FBX"
    icon = "code-fork"
    color = "orange"

    order = -10

    families = ["*"]
    representations = ["*"]
    extensions = {"fbx"}

    def load(self, context, name=None, namespace=None, data=None):

        # get file path from context
        file_path = self.filepath_from_context(context)
        file_path = file_path.replace("\\", "/")

        # get necessary data
        namespace, node_name = self.get_node_name(context, name, namespace)

        # create load tree
        nodes = self.create_load_node_tree(file_path, node_name, name)

        self[:] = nodes

        # Call containerise function which does some automations for you
        #  like moving created nodes to the AVALON_CONTAINERS subnetwork
        containerised_nodes = pipeline.containerise(
            node_name,
            namespace,
            nodes,
            context,
            self.__class__.__name__,
            suffix="",
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

        # Update the file path from representation
        file_path = get_representation_path(representation)
        file_path = file_path.replace("\\", "/")

        file_node.setParms({"file": file_path})

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()

    def switch(self, container, representation):
        self.update(container, representation)

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

        # Set new position for children nodes
        parent_node.layoutChildren()

        # Return all the nodes
        return [parent_node, file_node, attribdelete, null]
