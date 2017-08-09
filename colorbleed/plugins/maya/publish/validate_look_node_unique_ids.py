from collections import defaultdict

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateLookNodeUniqueIds(pyblish.api.InstancePlugin):
    """Validate look sets have unique colorbleed id attributes

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Id Unique Attributes'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.RepairAction]

    @staticmethod
    def get_invalid(instance):

        nodes = instance.data["lookData"]["sets"]

        # Ensure all nodes have a cbId
        id_sets = defaultdict(list)
        for node in nodes:
            unique_id = lib.get_id(node)
            if not unique_id:
                continue
            id_sets[unique_id].append(node)

        invalid = [n for n in id_sets.itervalues() if len(n) > 1]

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found without "
                               "asset IDs: {0}".format(invalid))
