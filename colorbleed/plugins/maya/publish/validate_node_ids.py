import maya.cmds as cmds

import pyblish.api
import colorbleed.api

from colorbleed.maya import lib


class ValidateNodeIDs(pyblish.api.InstancePlugin):
    """Validate nodes have a Colorbleed Id

    """

    order = colorbleed.api.ValidatePipelineOrder
    label = 'Node Ids (ID)'
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
        invalid = list()

        # TODO: Implement check on only nodes like on_save callback.
        instance_shape = cmds.ls(instance, type="shape")

        # We do want to check the referenced nodes as we it might be
        # part of the end product
        nodes = lib.filter_out_nodes(set(instance_shape), defaults=True)
        for node in nodes:
            if not lib.get_id(node):
                invalid.append(node)

        return invalid



