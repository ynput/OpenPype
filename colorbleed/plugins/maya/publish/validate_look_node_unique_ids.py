from collections import defaultdict
import pyblish.api
import colorbleed.api

import cbra.utils.maya.node_uuid as id_utils


class ValidateLookNodeUniqueIds(pyblish.api.InstancePlugin):
    """Validate look sets have unique colorbleed id attributes

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look Id Unique Attributes'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @staticmethod
    def get_invalid(instance):

        nodes = instance.data["lookSets"]

        # Ensure all nodes have a cbId
        id_sets = defaultdict(list)
        invalid = list()
        for node in nodes:
            id = id_utils.get_id(node)
            if not id:
                continue

            id_sets[id].append(node)

        for id, nodes in id_sets.iteritems():
            if len(nodes) > 1:
                invalid.extend(nodes)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Nodes found without "
                               "asset IDs: {0}".format(invalid))
