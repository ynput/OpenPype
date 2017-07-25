import os
import json

from maya import cmds
from avalon import api, maya
import colorbleed.maya.lib as lib


class LookLoader(api.Loader):
    """Specific loader for lookdev"""

    families = ["colorbleed.lookdev"]
    representations = ["ma"]

    label = "Reference look"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):
        """
        Load and try to ssign Lookdev to nodes based on relationship data
        Args:
            name:
            namespace:
            context:
            data:

        Returns:

        """

        reference_node = None

        # improve readability of the namespace
        assetname = context["asset"]["name"]
        ns_assetname = "{}_".format(assetname)

        namespace = maya.unique_namespace(ns_assetname,
                                          format="%03d",
                                          suffix="_look")

        try:
            reference_node = lib.get_reference_node(self.fname)
        except:
            pass

        if reference_node is None:
            self.log.info("Loading lookdev for the first time ...")
            with maya.maintained_selection():
                nodes = cmds.file(self.fname,
                                  namespace=namespace,
                                  reference=True,
                                  returnNewNodes=True)
        else:
            self.log.info("Reusing existing lookdev ...")
            nodes = cmds.referenceQuery(reference_node, nodes=True)

        # Assign shaders
        self.fname = self.fname.rsplit(".", 1)[0] + ".json"
        if not os.path.isfile(self.fname):
            self.log.warning("Look development asset "
                             "has no relationship data.")
            return nodes

        with open(self.fname) as f:
            relationships = json.load(f)

        # Get all nodes which belong to a matching name space
        # Currently this is the safest way to get all the nodes
        namespace_nodes = self.get_namespace_nodes(assetname)
        lib.apply_shaders(relationships, nodes, namespace_nodes)

        self[:] = nodes

    def get_namespace_nodes(self, assetname):
        """
        Get all nodes of namespace `asset_*` and check if they have a shader
        assigned, if not add to list
        Args:
            context (dict): current context of asset

        Returns:
            list

        """

        # types = ["transform", "mesh"]
        list_nodes = []

        namespaces = cmds.namespaceInfo(listOnlyNamespaces=True)

        # remove basic namespaces
        namespaces.remove("UI")
        namespaces.remove("shared")

        for ns in namespaces:
            if not ns.startswith(assetname):
                continue
            # get reference nodes
            ns_nodes = cmds.namespaceInfo(ns, listOnlyDependencyNodes=True)
            # TODO: might need to extend the types
            # check if any nodes are connected to something else than lambert1
            list_nodes = cmds.ls(ns_nodes, long=True)
            unassigned_nodes = [self.has_default_shader(n) for n in list_nodes]
            nodes = [n for n in unassigned_nodes if n is not None]

            list_nodes.extend(nodes)

        return set(list_nodes)

    def has_default_shader(self, node):
        """Check if the nodes have `initialShadingGroup` shader assigned

        Args:
            node (str): node to check

        Returns:
            str
        """

        shaders = cmds.listConnections(node, type="shadingEngine") or []
        if "initialShadingGroup" in shaders:
            # return transform node
            transform = cmds.listRelatives(node, parent=True, type="transform",
                                           fullPath=True)
            if not transform:
                return []

            return transform[0]
