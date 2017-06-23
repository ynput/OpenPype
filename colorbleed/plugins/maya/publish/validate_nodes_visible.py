import pyblish.api
import colorbleed.api

from maya import cmds
import cb.utils.maya.dag as dag


class ValidateNodesVisible(pyblish.api.InstancePlugin):
    """Validate all shape nodes are currently visible.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.furYeti']
    hosts = ['maya']
    label = "Nodes Visible"
    actions = [colorbleed.api.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        members = instance.data["setMembers"]
        members = cmds.ls(members,
                          dag=True,
                          shapes=True,
                          long=True,
                          noIntermediate=True)

        invalid = []
        for node in members:
            if not dag.is_visible(node, displayLayer=False):
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Instance contains invisible shapes: "
                             "{0}".format(invalid))
