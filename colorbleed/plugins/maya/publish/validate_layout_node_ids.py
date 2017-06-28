import pyblish.api
import colorbleed.api

import cbra.utils.maya.node_uuid as id_utils


class ValidateLayoutNodeIds(pyblish.api.InstancePlugin):
    """Validate nodes have colorbleed id attributes

    All non-referenced transform nodes in the hierarchy should have unique IDs

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.layout']
    hosts = ['maya']
    label = 'Layout Transform Ids'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @staticmethod
    def get_invalid(instance):

        from maya import cmds

        nodes = cmds.ls(instance, type='transform', long=True)
        referenced = cmds.ls(nodes, referencedNodes=True, long=True)
        non_referenced = set(nodes) - set(referenced)

        invalid = []
        for node in non_referenced:
            if not id_utils.get_id(node):
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Transforms (non-referenced) found in layout "
                               "without asset IDs: {0}".format(invalid))
