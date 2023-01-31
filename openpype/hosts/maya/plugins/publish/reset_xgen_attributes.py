from maya import cmds

import pyblish.api


class ResetXgenAttributes(pyblish.api.InstancePlugin):
    """Reset Xgen attributes."""

    label = "Reset Xgen Attributes."
    # Offset to run after workfile increment plugin.
    order = pyblish.api.IntegratorOrder + 10.0
    families = ["workfile"]

    def process(self, instance):
        xgen_attributes = instance.data.get("xgenAttributes", {})
        if not xgen_attributes :
            return

        for palette, data in xgen_attributes.items():
            for attr, value in data.items():
                node_attr = "{}.{}".format(palette, attr)
                self.log.info(
                    "Setting \"{}\" on \"{}\"".format(value, node_attr)
                )
                cmds.setAttr(node_attr, value, type="string")
            cmds.setAttr(palette + ".xgExportAsDelta", True)
            
        self.log.info("Saving changes.")
        cmds.file(save=True)
