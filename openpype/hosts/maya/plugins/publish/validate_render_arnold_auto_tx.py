from maya import cmds

import pyblish.api
import openpype.api

from openpype.hosts.maya.api.lib_rendersetup import get_attr_in_layer


class ValidateRenderArnoldAutoTx(pyblish.api.InstancePlugin):
    """Validates Arnold's autogenerate .tx files on render is disabled."""

    order = openpype.api.ValidateContentsOrder
    label = "Arnold Auto-Convert Textures to TX off"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [openpype.api.RepairAction]

    def process(self, instance):

        renderer = instance.data.get("renderer")
        layer = instance.data['setMembers']
        if renderer != "arnold":
            self.log.info("Skipping because renderer is not Arnold. "
                          "Renderer: {}".format(renderer))
            return

        plug = "defaultArnoldRenderOptions.autotx"
        if get_attr_in_layer(plug, layer=layer):
            raise RuntimeError("Arnold Auto TX is enabled. "
                               "Should be disabled.")

    @classmethod
    def repair(cls, instance):
        plug = "defaultArnoldRenderOptions.autotx"
        if cmds.getAttr(plug):
            print("Disabling {}".format(plug))
            cmds.setAttr(plug, False)
