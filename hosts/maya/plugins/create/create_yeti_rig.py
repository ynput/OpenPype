from maya import cmds

from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateYetiRig(plugin.Creator):
    """Output for procedural plugin nodes ( Yeti / XGen / etc)"""

    label = "Yeti Rig"
    family = "yetiRig"
    icon = "usb"

    def process(self):

        with lib.undo_chunk():
            instance = super(CreateYetiRig, self).process()

            self.log.info("Creating Rig instance set up ...")
            input_meshes = cmds.sets(name="input_SET", empty=True)
            cmds.sets(input_meshes, forceElement=instance)
