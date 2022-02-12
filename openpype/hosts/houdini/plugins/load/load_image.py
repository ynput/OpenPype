import os

from avalon import api
from openpype.hosts.houdini.api import lib, pipeline

import hou


def get_image_avalon_container():
    """The COP2 files must be in a COP2 network.

    So we maintain a single entry point within AVALON_CONTAINERS,
    just for ease of use.

    """

    path = pipeline.AVALON_CONTAINERS
    avalon_container = hou.node(path)
    if not avalon_container:
        # Let's create avalon container secretly
        # but make sure the pipeline still is built the
        # way we anticipate it was built, asserting it.
        assert path == "/obj/AVALON_CONTAINERS"

        parent = hou.node("/obj")
        avalon_container = parent.createNode(
            "subnet", node_name="AVALON_CONTAINERS"
        )

    image_container = hou.node(path + "/IMAGES")
    if not image_container:
        image_container = avalon_container.createNode(
            "cop2net", node_name="IMAGES"
        )
        image_container.moveToGoodPosition()

    return image_container


class ImageLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.imagesequence"]
    label = "Load Image (COP2)"
    representations = ["*"]
    order = -10

    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        # Format file name, Houdini only wants forward slashes
        file_path = os.path.normpath(self.fname)
        file_path = file_path.replace("\\", "/")
        file_path = self._get_file_sequence(file_path)

        # Get the root node
        parent = get_image_avalon_container()

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        node = parent.createNode("file", node_name=node_name)
        node.moveToGoodPosition()

        node.setParms({"filename1": file_path})

        # Imprint it manually
        data = {
            "schema": "avalon-core:container-2.0",
            "id": pipeline.AVALON_CONTAINER_ID,
            "name": node_name,
            "namespace": namespace,
            "loader": str(self.__class__.__name__),
            "representation": str(context["representation"]["_id"]),
        }

        # todo: add folder="Avalon"
        lib.imprint(node, data)

        return node

    def update(self, container, representation):

        node = container["node"]

        # Update the file path
        file_path = api.get_representation_path(representation)
        file_path = file_path.replace("\\", "/")
        file_path = self._get_file_sequence(file_path)

        # Update attributes
        node.setParms(
            {
                "filename1": file_path,
                "representation": str(representation["_id"]),
            }
        )

    def remove(self, container):

        node = container["node"]

        # Let's clean up the IMAGES COP2 network
        # if it ends up being empty and we deleted
        # the last file node. Store the parent
        # before we delete the node.
        parent = node.parent()

        node.destroy()

        if not parent.children():
            parent.destroy()

    def _get_file_sequence(self, root):
        files = sorted(os.listdir(root))

        first_fname = files[0]
        prefix, padding, suffix = first_fname.rsplit(".", 2)
        fname = ".".join([prefix, "$F{}".format(len(padding)), suffix])
        return os.path.join(root, fname).replace("\\", "/")
