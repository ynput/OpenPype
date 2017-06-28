from collections import defaultdict

from maya import cmds

import pyblish.api
import colorbleed.api

import cbra.utils.maya.node_uuid as id_utils


class ValidateLookMembersUnique(pyblish.api.InstancePlugin):
    """Validate members of look are unique.

    This ensures the same id is not present as more than one node in the look.

    That means there's only ever one of a specific node inside the look to be
    published. For example if you'd have a loaded 3x the same tree and by
    accident you're trying to publish them all together in a single look that
    would be invalid, because they are the same tree it should be included
    inside the look instance only once.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look Members Unique'
    actions = [colorbleed.api.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        # Get all members from the sets
        members = []
        relations = instance.data["lookData"]["sets"]
        for sg in relations:
            sg_members = sg['members']
            sg_members = [member['name'] for member in sg_members]
            members.extend(sg_members)

        # Ensure we don't have components but the objects
        members = cmds.ls(members, objectsOnly=True, long=True)
        members = list(set(members))

        # Group members per id
        id_nodes = defaultdict(set)
        for node in members:
            node_id = id_utils.get_id(node)
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
            raise RuntimeError("Members found without "
                               "asset IDs: {0}".format(invalid))
