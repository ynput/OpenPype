import pype.maya.plugin
from avalon import api, io
import json
import pype.maya.lib

class LookLoader(pype.maya.plugin.ReferenceLoader):
    """Specific loader for lookdev"""

    families = ["look"]
    representations = ["ma"]

    label = "Reference look"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):
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
        self.log.info("container {}".format(container))
        shader_nodes = members

        nodes = []
        for shader in shader_nodes:
            nodes.append(cmds.listConnections(cmds.listHistory(shader, f=1), type='mesh'))
        self.log.info("nodes {}".format(nodes))

        json_representation = io.find_one({"type": "representation",
                                           "parent": representation['parent'],
                                           "name": "json"})
        self.log.info("Found json representation {}".format(json_representation))

        # Load relationships
        shader_relation = api.get_representation_path(json_representation)
        with open(shader_relation, "r") as f:
            relationships = json.load(f)


        # Assign relationships
        pype.maya.lib.apply_shaders(relationships, shader_nodes, nodes)

        # Update metadata
        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")
