import os
import re
from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import pipeline
from openpype.pipeline.load import LoadError

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
            raise LoadError("Unable to initialize geo node with Redshift "
                            "attributes. Make sure you have the Redshift "
                            "plug-in set up correctly for Houdini.")

        # Enable by default
        container.setParms({
            "RS_objprop_proxy_enable": True,
            "RS_objprop_proxy_file": self.format_path(
                self.filepath_from_context(context),
                context["representation"])
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
            "RS_objprop_proxy_file": self.format_path(
                file_path, representation)
        })

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()

    @staticmethod
    def format_path(path, representation):
        """Format file path correctly for single redshift proxy
        or redshift proxy sequence."""
        if not os.path.exists(path):
            raise RuntimeError("Path does not exist: %s" % path)

        is_sequence = bool(representation["context"].get("frame"))
        # The path is either a single file or sequence in a folder.
        if is_sequence:
            filename = re.sub(r"(.*)\.(\d+)\.(rs.*)", "\\1.$F4.\\3", path)
            filename = os.path.join(path, filename)
        else:
            filename = path

        filename = os.path.normpath(filename)
        filename = filename.replace("\\", "/")

        return filename
