import os
import json

from maya import cmds
from avalon import api, maya


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

        # improve readability of the namespace
        assetname = context["asset"]["name"]
        ns_assetname = "{}_".format(assetname)

        namespace = maya.unique_namespace(ns_assetname,
                                          format="%03d",
                                          suffix="_look")
        try:
            existing_reference = cmds.file(self.fname,
                                           query=True,
                                           referenceNode=True)
        except RuntimeError as e:
            if e.message.rstrip() != "Cannot find the scene file.":
                raise

            self.log.info("Loading lookdev for the first time..")
            with maya.maintained_selection():
                nodes = cmds.file(self.fname,
                                  namespace=namespace,
                                  reference=True,
                                  returnNewNodes=True)
        else:
            self.log.info("Reusing existing lookdev..")
            nodes = cmds.referenceQuery(existing_reference, nodes=True)

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
        self.apply_shaders(relationships, nodes, namespace_nodes)

        self[:] = nodes

    def apply_shaders(self, relationships, nodes, namespace_nodes):
        """Apply all shaders to the nodes based on the relationship data

        Args:
            relationships (dict): shader to node relationships
            nodes (list): shader network nodes
            namespace_nodes (list): nodes from linked to namespace

        Returns:
            None
        """

        # attributes = relationships.get("attributes", [])
        sets = relationships.get("sets", [])

        shading_engines = cmds.ls(nodes, type="shadingEngine", long=True)
        assert len(shading_engines) > 0, ("Error in retrieving shading engine "
                                          "from reference")

        # get all nodes which we need to link
        for set in sets:
            # collect all unique IDs of the set members
            uuid = set["uuid"]
            member_uuids = [member["uuid"] for member in set["members"]]
            filtered_nodes = self.get_matching_nodes(namespace_nodes,
                                                     member_uuids)
            shading_engine = self.get_matching_nodes(shading_engines,
                                                     [uuid])

            assert len(shading_engine) == 1, ("Could not find the correct "
                                              "shading engine with cbId "
                                              "'{}'".format(uuid))

            cmds.sets(filtered_nodes, forceElement=shading_engine[0])

    def get_matching_nodes(self, nodes, uuids):
        """Filter all nodes which match the UUIDs

        Args:
            nodes (list): collection of nodes to check
            uuids (list): a list of UUIDs which are linked to the shader

        Returns:
            list: matching nodes
        """

        filtered_nodes = []
        for node in nodes:
            if node is None:
                continue

            if not cmds.attributeQuery("cbId", node=node, exists=True):
                continue

            # Deformed shaped
            attr = "{}.cbId".format(node)
            attribute_value = cmds.getAttr(attr)

            if attribute_value not in uuids:
                continue

            filtered_nodes.append(node)

        return filtered_nodes

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
