from avalon import api

from avalon.houdini import pipeline, lib


class CameraLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["camera"]
    label = "Load Camera (abc)"
    representations = ["abc"]
    order = -10

    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import os
        import hou

        # Format file name, Houdini only wants forward slashes
        file_path = os.path.normpath(self.fname)
        file_path = file_path.replace("\\", "/")

        # Get the root node
        obj = hou.node("/obj")

        # Create a unique name
        counter = 1
        asset_name = context["asset"]["name"]

        namespace = namespace if namespace else asset_name
        formatted = "{}_{}".format(namespace, name) if namespace else name
        node_name = "{0}_{1:03d}".format(formatted, counter)

        children = lib.children_as_string(hou.node("/obj"))
        while node_name in children:
            counter += 1
            node_name = "{0}_{1:03d}".format(formatted, counter)

        # Create a archive node
        container = self.create_and_connect(obj, "alembicarchive", node_name)

        # TODO: add FPS of project / asset
        container.setParms({"fileName": file_path,
                            "channelRef": True})

        # Apply some magic
        container.parm("buildHierarchy").pressButton()
        container.moveToGoodPosition()

        # Create an alembic xform node
        nodes = [container]

        self[:] = nodes

        return pipeline.containerise(node_name,
                                     namespace,
                                     nodes,
                                     context,
                                     self.__class__.__name__)

    def update(self, container, representation):

        node = container["node"]

        # Update the file path
        file_path = api.get_representation_path(representation)
        file_path = file_path.replace("\\", "/")

        # Update attributes
        node.setParms({"fileName": file_path,
                       "representation": str(representation["_id"])})

        # Rebuild
        node.parm("buildHierarchy").pressButton()

    def remove(self, container):

        node = container["node"]
        node.destroy()

    def create_and_connect(self, node, node_type, name=None):
        """Create a node within a node which and connect it to the input

        Args:
            node(hou.Node): parent of the new node
            node_type(str) name of the type of node, eg: 'alembic'
            name(str, Optional): name of the node

        Returns:
            hou.Node

        """

        import hou

        try:

            if name:
                new_node = node.createNode(node_type, node_name=name)
            else:
                new_node = node.createNode(node_type)

            new_node.moveToGoodPosition()

            try:
                input_node = next(i for i in node.allItems() if
                                  isinstance(i, hou.SubnetIndirectInput))
            except StopIteration:
                return new_node

            new_node.setInput(0, input_node)
            return new_node

        except Exception:
            raise RuntimeError("Could not created node type `%s` in node `%s`"
                               % (node_type, node))
