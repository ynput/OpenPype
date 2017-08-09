from collections import defaultdict

from maya import cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateNonDuplicateRelationshipMembers(pyblish.api.InstancePlugin):
    """Validate the relational nodes of the look data to ensure every node is
    unique.

    This ensures the same id is not present as more than one node in the look.

    That means there's only ever one of a specific node inside the look to be
    published. For example if you'd have a loaded 3x the same tree and by
    accident you're trying to publish them all together in a single look that
    would be invalid, because they are the same tree it should be included
    inside the look instance only once.

    """

    order = colorbleed.api.ValidatePipelineOrder
    label = 'Non Duplicate Relationship Members (ID)'
    hosts = ['maya']
    families = ['colorbleed.lookdev']

    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @staticmethod
    def get_invalid(instance):

        # Get all members from the sets
        members = []
        relationships = instance.data["lookData"]["relationships"]
        for relationship in relationships:
            members.extend([i['name'] for i in relationship['members']])

        # Ensure we don't have components but the objects
        members = set(cmds.ls(members, objectsOnly=True, long=True))
        members = list(members)

        # Group members per id
        id_nodes = defaultdict(set)
        for node in members:
            node_id = lib.get_id(node)
            if not node_id:
                continue
            id_nodes[node_id].add(node)

        invalid = [n for n in id_nodes.itervalues() if len(n) > 1]

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Members found without asset IDs: "
                               "{0}".format(invalid))
