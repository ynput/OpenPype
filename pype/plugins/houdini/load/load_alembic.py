from avalon import api

from avalon.houdini import pipeline, lib


class AbcLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["model",
                "animation",
                "pointcache"]
    label = "Load Alembic"
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
        namespace = namespace if namespace else context["asset"]["name"]
        formatted = "{}_{}".format(namespace, name) if namespace else name
        node_name = "{0}_{1:03d}".format(formatted, counter)

        children = lib.children_as_string(hou.node("/obj"))
        while node_name in children:
            counter += 1
            node_name = "{0}_{1:03d}".format(formatted, counter)

        # Create a new geo node
        container = obj.createNode("geo", node_name=node_name)

        # Remove the file node, it only loads static meshes
        # Houdini 17 has removed the file node from the geo node
        file_node = container.node("file1")
        if file_node:
            file_node.destroy()

        # Create an alembic node (supports animation)
        alembic = container.createNode("alembic", node_name=node_name)
        alembic.setParms({"fileName": file_path})

        # Add unpack node
        unpack_name = "unpack_{}".format(name)
        unpack = container.createNode("unpack", node_name=unpack_name)
        unpack.setInput(0, alembic)
        unpack.setParms({"transfer_attributes": "path"})

        # Add normal to points
        # Order of menu ['point', 'vertex', 'prim', 'detail']
        normal_name = "normal_{}".format(name)
        normal_node = container.createNode("normal", node_name=normal_name)
        normal_node.setParms({"type": 0})

        normal_node.setInput(0, unpack)

        null = container.createNode("null", node_name="OUT".format(name))
        null.setInput(0, normal_node)

        # Set display on last node
        null.setDisplayFlag(True)

        # Set new position for unpack node else it gets cluttered
        nodes = [container, alembic, unpack, normal_node, null]
        for nr, node in enumerate(nodes):
            node.setPosition([0, (0 - nr)])

        self[:] = nodes

        return pipeline.containerise(node_name,
                                     namespace,
                                     nodes,
                                     context,
                                     self.__class__.__name__)

    def update(self, container, representation):

        node = container["node"]
        try:
            alembic_node = next(n for n in node.children() if
                                n.type().name() == "alembic")
        except StopIteration:
            self.log.error("Could not find node of type `alembic`")
            return

        # Update the file path
        file_path = api.get_representation_path(representation)
        file_path = file_path.replace("\\", "/")

        alembic_node.setParms({"fileName": file_path})

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()
