import pyblish.api
import colorbleed.api


class ValidateLookNodeIds(pyblish.api.InstancePlugin):
    """Validate nodes have colorbleed id attributes

    All look sets should have id attributes.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look Id Attributes'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @staticmethod
    def get_invalid(instance):
        import maya.cmds as cmds

        nodes = instance.data["lookSets"]

        # Ensure all nodes have a cbId
        invalid = list()
        for node in nodes:
            uuid = cmds.attributeQuery("mbId", node=node, exists=True)
            if not uuid:
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Nodes found without "
                               "asset IDs: {0}".format(invalid))
