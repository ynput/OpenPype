from maya import cmds

import pyblish.api


class ResetXgenAttributes(pyblish.api.InstancePlugin):
    """Reset Xgen attributes.

    When the incremental save of the workfile triggers, the Xgen attributes
    changes so this plugin will change it back to the values before publishing.
    """

    label = "Reset Xgen Attributes."
    # Offset to run after workfile increment plugin.
    order = pyblish.api.IntegratorOrder + 10.0
    families = ["workfile"]

    def process(self, instance):
        xgen_attributes = instance.data.get("xgenAttributes", {})
        if not xgen_attributes:
            return

        for palette, data in xgen_attributes.items():
            for attr, value in data.items():
                node_attr = "{}.{}".format(palette, attr)
                self.log.debug(
                    "Setting \"{}\" on \"{}\"".format(value, node_attr)
                )
                cmds.setAttr(node_attr, value, type="string")
            cmds.setAttr(palette + ".xgExportAsDelta", True)

        # Need to save the scene, cause the attribute changes above does not
        # mark the scene as modified so user can exit without committing the
        # changes.
        self.log.debug("Saving changes.")
        cmds.file(save=True)
