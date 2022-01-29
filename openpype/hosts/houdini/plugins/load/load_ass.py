import os

from avalon import api
from avalon.houdini import pipeline
import clique


class AssLoader(api.Loader):
    """Load .ass with Arnold Procedural"""

    families = ["ass"]
    label = "Load Arnold Procedural"
    representations = ["ass"]
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
        procedural = obj.createNode("arnold::procedural", node_name=node_name)
        procedural.setParms({"ar_filename": self.get_path(self.fname)})

        nodes = [procedural]
        self[:] = nodes

        return pipeline.containerise(
            node_name,
            namespace,
            nodes,
            context,
            self.__class__.__name__,
            suffix="",
        )

    def get_path(self, path):

        # Find all frames in the folder
        ext = ".ass.gz" if path.endswith(".ass.gz") else ".ass"
        folder = os.path.dirname(path)
        frames = [f for f in os.listdir(folder) if f.endswith(ext)]

        # Get the collection of frames to detect frame padding
        patterns = [clique.PATTERNS["frames"]]
        collections, remainder = clique.assemble(frames,
                                                 minimum_items=1,
                                                 patterns=patterns)
        assert len(collections) == 1
        assert not remainder
        collection = collections[0]

        num_frames = len(collection.indexes)
        if num_frames == 1:
            # Return the input path without dynamic $F variable
            result = path
        else:
            fname = "{}$F{}{}".format(collection.head,
                                      collection.padding,
                                      collection.tail)
            result = os.path.join(folder, fname)

        # Format file name, Houdini only wants forward slashes
        return os.path.normpath(result).replace("\\", "/")

    def update(self, container, representation):

        # Update the file path
        file_path = api.get_representation_path(representation)
        file_path = file_path.replace("\\", "/")

        procedural = container["node"]
        procedural.setParms({"ar_filename": file_path})

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()
