import avalon.api

from avalon.houdini import pipeline, lib
reload(pipeline)
reload(lib)


class AbcLoader(avalon.api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation", "colorbleed.pointcache"]
    label = "Reference animation"
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
        node_path = "/obj/{}/file1".format(node_name)
        file_node = hou.node(node_path)
        file_node.destroy()

        # Create an alembic node (supports animation)
        alembic = container.createNode("alembic", node_name=node_name)
        alembic.setParms({"fileName": file_path})

        # Add unpack node
        unpack = container.createNode("unpack")
        unpack.setInput(0, alembic)
        unpack.setParms({"transfer_attributes": "path"})

        # Set new position for unpack node else it gets cluttered
        unpack.setPosition([0, -1])

        # set unpack as display node
        unpack.setDisplayFlag(True)

        null_node = container.createNode("null",
                                         node_name="OUT_{}".format(name))
        null_node.setPosition([0, -2])
        null_node.setInput(0, unpack)

        nodes = [container, alembic, unpack, null_node]

        self[:] = nodes

        return pipeline.containerise(node_name,
                                     namespace,
                                     nodes,
                                     context,
                                     self.__class__.__name__)

    def update(self, container, representation):
        pass

    def remove(self, container):
        print(">>>", container["objectName"])
