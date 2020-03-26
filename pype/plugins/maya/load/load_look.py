import pype.maya.plugin
from avalon import api, io
import json
import pype.maya.lib
from collections import defaultdict


class LookLoader(pype.maya.plugin.ReferenceLoader):
    """Specific loader for lookdev"""

    families = ["look"]
    representations = ["ma"]

    label = "Reference look"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, options):
        """
        Load and try to assign Lookdev to nodes based on relationship data
        Args:
            name:
            namespace:
            context:
            data:

        Returns:

        """

        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True)

        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):

        import os
        from maya import cmds

        node = container["objectName"]

        path = api.get_representation_path(representation)

        # Get reference node from container members
        members = cmds.sets(node, query=True, nodesOnly=True)
        reference_node = self._get_reference_node(members)

        file_type = {
            "ma": "mayaAscii",
            "mb": "mayaBinary",
            "abc": "Alembic"
        }.get(representation["name"])

        assert file_type, "Unsupported representation: %s" % representation

        assert os.path.exists(path), "%s does not exist." % path

        try:
            content = cmds.file(path,
                                loadReference=reference_node,
                                type=file_type,
                                returnNewNodes=True)
        except RuntimeError as exc:
            # When changing a reference to a file that has load errors the
            # command will raise an error even if the file is still loaded
            # correctly (e.g. when raising errors on Arnold attributes)
            # When the file is loaded and has content, we consider it's fine.
            if not cmds.referenceQuery(reference_node, isLoaded=True):
                raise

            content = cmds.referenceQuery(reference_node,
                                          nodes=True,
                                          dagPath=True)
            if not content:
                raise

            self.log.warning("Ignoring file read error:\n%s", exc)

        # Fix PLN-40 for older containers created with Avalon that had the
        # `.verticesOnlySet` set to True.
        if cmds.getAttr("{}.verticesOnlySet".format(node)):
            self.log.info("Setting %s.verticesOnlySet to False", node)
            cmds.setAttr("{}.verticesOnlySet".format(node), False)

        # Add new nodes of the reference to the container
        cmds.sets(content, forceElement=node)

        # Remove any placeHolderList attribute entries from the set that
        # are remaining from nodes being removed from the referenced file.
        members = cmds.sets(node, query=True)
        invalid = [x for x in members if ".placeHolderList" in x]
        if invalid:
            cmds.sets(invalid, remove=node)

        # Get container members
        shader_nodes = cmds.ls(members, type='shadingEngine')

        nodes_list = []
        for shader in shader_nodes:
            connections = cmds.listConnections(cmds.listHistory(shader, f=1),
                                               type='mesh')
            if connections:
                for connection in connections:
                    nodes_list.extend(cmds.listRelatives(connection,
                                                         shapes=True))
        nodes = set(nodes_list)

        json_representation = io.find_one({
            "type": "representation",
            "parent": representation['parent'],
            "name": "json"
        })

        # Load relationships
        shader_relation = api.get_representation_path(json_representation)
        with open(shader_relation, "r") as f:
            relationships = json.load(f)

        attributes = relationships.get("attributes", [])

        # region compute lookup
        nodes_by_id = defaultdict(list)
        for n in nodes:
            nodes_by_id[pype.maya.lib.get_id(n)].append(n)

        pype.maya.lib.apply_attributes(attributes, nodes_by_id)

        # Update metadata
        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")
