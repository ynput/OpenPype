from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateYetiRigInputShapesRequired(pyblish.api.Validator):
    """Validate if all input nodes have at least one incoming connection"""

    order = colorbleed.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["colorbleed.yetiRig"]
    label = "Yeti Rig Input Shapes Required"
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Yeti Rig has invalid input meshes")

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        input_set = [i for i in instance if i == "input_SET"][0]
        input_nodes = cmds.sets(input_set, query=True)
        for node in input_nodes:
            incoming = cmds.listConnections(node,
                                            source=True,
                                            destination=False,
                                            connections=True,
                                            plugs=True)
            if not incoming:
                invalid.append(node)

        return invalid
