from collections import defaultdict

import pyblish.api
import colorbleed.api


class ValidateUniqueRelationshipMembers(pyblish.api.InstancePlugin):
    """Validate the relational nodes of the look data to ensure every node is
    unique.

    This ensures the all member ids are unique.

    That means there's only ever one of a specific node inside the look to be
    published. For example if you'd have a loaded 3x the same tree and by
    accident you're trying to publish them all together in a single look that
    would be invalid, because they are the same tree it should be included
    inside the look instance only once.

    """

    order = colorbleed.api.ValidatePipelineOrder
    label = 'Unique Relationship Members (ID)'
    hosts = ['maya']
    families = ['colorbleed.lookdev']

    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Members found without asset IDs: "
                               "{0}".format(invalid))

    @staticmethod
    def get_invalid(instance):

        # Get all members from the sets
        id_nodes = defaultdict(list)
        relationships = instance.data["lookData"]["relationships"]
        for relationship in relationships.values():
            for member in relationship['members']:
                node_id = member["uuid"]
                node = member["name"]
                id_nodes[node_id].append(node)

        # check if any id has more than 1 node
        invalid = []
        for nodes in id_nodes.values():
            if len(nodes) > 1:
                invalid.extend(nodes)

        return invalid
