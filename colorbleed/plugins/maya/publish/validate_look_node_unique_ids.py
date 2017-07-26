from collections import defaultdict

import maya.cmds as cmds

import pyblish.api
import colorbleed.api


class ValidateLookNodeUniqueIds(pyblish.api.InstancePlugin):
    """Validate look sets have unique colorbleed id attributes

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look Id Unique Attributes'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.RepairAction]

    @staticmethod
    def get_invalid(instance):

        nodes = instance.data["lookData"]["sets"]

        # Ensure all nodes have a cbId
        id_sets = defaultdict(list)
        invalid = list()
        for node in nodes:
            unique_id = None
            if cmds.attributeQuery("mbId", node=node, exists=True):
                unique_id = cmds.getAttr("{}.mbId".format(node))
            if not unique_id:
                continue

            id_sets[unique_id].append(node)

        for unique_id, nodes in id_sets.iteritems():
            if len(nodes) > 1:
                invalid.extend(nodes)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found without "
                               "asset IDs: {0}".format(invalid))
