from collections import defaultdict

from maya import cmds

import pyblish.api
import colorbleed.api


def get_unique_id(node):
    attr = 'cbId'
    unique_id = None
    has_attribute = cmds.attributeQuery(attr, node=node, exists=True)
    if has_attribute:
        unique_id = cmds.getAttr("{}.{}".format(node, attr))
    return unique_id


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
        for sg in relationships:
            sg_members = [member['name'] for member in sg['members']]
            members.extend(sg_members)

        # Ensure we don't have components but the objects
        members = cmds.ls(members, objectsOnly=True, long=True)
        members = list(set(members))

        # Group members per id
        id_nodes = defaultdict(set)
        for node in members:
            node_id = get_unique_id(node)
            if not node_id:
                continue
            id_nodes[node_id].add(node)

        invalid = list()
        for nodes in id_nodes.itervalues():
            if len(nodes) > 1:
                invalid.extend(nodes)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Members found without asset IDs: "
                               "{0}".format(invalid))
