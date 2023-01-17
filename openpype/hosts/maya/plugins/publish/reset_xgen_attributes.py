from maya import cmds

import pyblish.api


class ResetXgenAttributes(pyblish.api.InstancePlugin):
    """Reset Xgen attributes."""

    label = "Reset Xgen Attributes."
    # Offset to run after global integrator.
    order = pyblish.api.IntegratorOrder + 1.0
    families = ["workfile"]

    def process(self, instance):
        for palette, data in instance.data.get("xgenAttributes", {}).items():
            for attr, value in data.items():
                node_attr = "{}.{}".format(palette, attr)
                self.log.info(
                    "Setting \"{}\" on \"{}\"".format(value, node_attr)
                )
                cmds.setAttr(node_attr, value, type="string")
