import maya.cmds as cmds

import pyblish.api
import colorbleed.api

from colorbleed.maya import lib


class ValidateNodeIDs(pyblish.api.InstancePlugin):
    """Validate nodes have a Colorbleed Id

    """

    order = colorbleed.api.ValidatePipelineOrder
    label = 'Instance Nodes Have ID'
    hosts = ['maya']
    families = ["colorbleed.model",
                "colorbleed.lookdev",
                "colorbleed.rig"]

    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found without "
                               "IDs: {0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""

        # We do want to check the referenced nodes as it might be
        # part of the end product
        id_nodes = lib.get_id_required_nodes(defaults=True,
                                             referenced_nodes=False)

        nodes = instance[:]
        invalid = [n for n in nodes if n in id_nodes and not lib.get_id(n)]

        return invalid
