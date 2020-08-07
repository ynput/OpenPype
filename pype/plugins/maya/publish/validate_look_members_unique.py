from collections import defaultdict

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateUniqueRelationshipMembers(pyblish.api.InstancePlugin):
    """Validate the relational nodes of the look data to ensure every node is
    unique.

    This ensures the all member ids are unique. Every node id must be from
    a single node in the scene.

    That means there's only ever one of a specific node inside the look to be
    published. For example if you'd have a loaded 3x the same tree and by
    accident you're trying to publish them all together in a single look that
    would be invalid, because they are the same tree. It should be included
    inside the look instance only once.

    """

    order = pype.api.ValidatePipelineOrder
    label = 'Look members unique'
    hosts = ['maya']
    families = ['look']

    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.hosts.maya.action.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Members found without non-unique IDs: "
                               "{0}".format(invalid))

    @staticmethod
    def get_invalid(instance):
        """
        Check all the relationship members of the objectSets

        Example of the lookData relationships:
        {"uuid": 59b2bb27bda2cb2776206dd8:79ab0a63ffdf,
         "members":[{"uuid": 59b2bb27bda2cb2776206dd8:1b158cc7496e,
                     "name": |model_GRP|body_GES|body_GESShape}
                     ...,
                     ...]}

        Args:
            instance:

        Returns:

        """

        # Get all members from the sets
        id_nodes = defaultdict(set)
        relationships = instance.data["lookData"]["relationships"]

        for relationship in relationships.values():
            for member in relationship['members']:
                node_id = member["uuid"]
                node = member["name"]
                id_nodes[node_id].add(node)

        # Check if any id has more than 1 node
        invalid = []
        for nodes in id_nodes.values():
            if len(nodes) > 1:
                invalid.extend(nodes)

        return invalid
