import pyblish.api
import colorbleed.api


class ValidateNodeIds(pyblish.api.InstancePlugin):
    """Validate nodes have colorbleed id attributes

    All look sets should have id attributes.

    """

    label = 'Node Id Attributes'
    families = ['colorbleed.look', 'colorbleed.model']
    hosts = ['maya']
    order = colorbleed.api.ValidatePipelineOrder
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @staticmethod
    def get_invalid(instance):
        import maya.cmds as cmds

        nodes = instance.data["setMembers"]

        # Ensure all nodes have a cbId
        data_id = {}
        invalid = []
        for node in nodes:
            try:
                uuid = cmds.getAttr("{}.cbId".format(node))
                data_id[uuid] = node
                if uuid in data_id:
                    invalid.append(node)
            except RuntimeError:
                pass

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Nodes found with invalid"
                               "asset IDs: {0}".format(invalid))
