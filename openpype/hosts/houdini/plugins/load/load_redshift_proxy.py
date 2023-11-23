import os
from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import pipeline

import clique
import hou


class RedshiftProxyLoader(load.LoaderPlugin):
    """Load Redshift Proxy"""

    families = ["redshiftproxy"]
    label = "Load Redshift Proxy"
    representations = ["rs"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        # Get the root node
        obj = hou.node("/obj")

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        # Create a new geo node
        container = obj.createNode("geo", node_name=node_name)

        # Check whether the Redshift parameters exist - if not, then likely
        # redshift is not set up or initialized correctly
        if not container.parm("RS_objprop_proxy_enable"):
            container.destroy()
            raise RuntimeError("Unable to initialize geo node with Redshift "
                               "attributes. Make sure you have the Redshift "
                               "plug-in set up correctly for Houdini.")

        # Enable by default
        container.setParms({
            "RS_objprop_proxy_enable": True,
            "RS_objprop_proxy_file": self.format_path(self.fname)
        })

        # Remove the file node, it only loads static meshes
        # Houdini 17 has removed the file node from the geo node
        file_node = container.node("file1")
        if file_node:
            file_node.destroy()

        # Add this stub node inside so it previews ok
        proxy_sop = container.createNode("redshift_proxySOP",
                                         node_name=node_name)
        proxy_sop.setDisplayFlag(True)

        nodes = [container, proxy_sop]

        self[:] = nodes

        return pipeline.containerise(
            node_name,
            namespace,
            nodes,
            context,
            self.__class__.__name__,
            suffix="",
        )

    def update(self, container, representation):

        # Update the file path
        file_path = get_representation_path(representation)

        node = container["node"]
        node.setParms({
            "RS_objprop_proxy_file": self.format_path(file_path)
        })

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()

    def format_path(self, path):
        """Format using $F{padding} token if sequence, otherwise just path."""

        # Find all frames in the folder
        ext = ".rs"
        folder = os.path.dirname(path)
        frames = [f for f in os.listdir(folder) if f.endswith(ext)]

        # Get the collection of frames to detect frame padding
        patterns = [clique.PATTERNS["frames"]]
        collections, remainder = clique.assemble(frames,
                                                 minimum_items=1,
                                                 patterns=patterns)
        self.log.debug("Detected collections: {}".format(collections))
        self.log.debug("Detected remainder: {}".format(remainder))

        if not collections and remainder:
            if len(remainder) != 1:
                raise ValueError("Frames not correctly detected "
                                 "in: {}".format(remainder))

            # A single frame without frame range detected
            return os.path.normpath(path).replace("\\", "/")

        # Frames detected with a valid "frame" number pattern
        # Then we don't want to have any remainder files found
        assert len(collections) == 1 and not remainder
        collection = collections[0]

        num_frames = len(collection.indexes)
        if num_frames == 1:
            # Return the input path without dynamic $F variable
            result = path
        else:
            # More than a single frame detected - use $F{padding}
            fname = "{}$F{}{}".format(collection.head,
                                      collection.padding,
                                      collection.tail)
            result = os.path.join(folder, fname)

        # Format file name, Houdini only wants forward slashes
        return os.path.normpath(result).replace("\\", "/")
