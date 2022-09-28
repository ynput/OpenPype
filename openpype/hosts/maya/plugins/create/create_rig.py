from maya import cmds

from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateRig(plugin.Creator):
    """Artist-friendly rig with controls to direct motion"""

    name = "rigDefault"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"

    def process(self):

        with lib.undo_chunk():
            instance = super(CreateRig, self).process()

            self.log.info("Creating Rig instance set up ...")
            controls = cmds.sets(name="controls_SET", empty=True)
            pointcache = cmds.sets(name="out_SET", empty=True)
            cmds.sets([controls, pointcache], forceElement=instance)
