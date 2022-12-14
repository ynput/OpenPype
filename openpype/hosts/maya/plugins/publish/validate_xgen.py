import maya.cmds as cmds

import pyblish.api


class ValidateXgen(pyblish.api.InstancePlugin):
    """Ensure Xgen objectset only contains collections."""

    label = "Xgen"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    families = ["xgen"]

    def process(self, instance):
        nodes = (
            cmds.ls(instance, type="xgmPalette", long=True) +
            cmds.ls(instance, type="transform", long=True) +
            cmds.ls(instance, type="xgmDescription", long=True) +
            cmds.ls(instance, type="xgmSubdPatch", long=True)
        )
        remainder_nodes = []
        for node in instance:
            if node in nodes:
                continue
            remainder_nodes.append(node)

        msg = "Invalid nodes in the objectset:\n{}".format(remainder_nodes)
        assert not remainder_nodes, msg
