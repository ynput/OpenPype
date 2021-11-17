from maya import cmds

from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateAnimLib(plugin.Creator):
    """Studio Library animlib """

    name = "animlibDefault"
    label = "AnimLib"
    family = "animlib"
    icon = "wheelchair"
    defaults = ['Main']

    def process(self):

        with lib.undo_chunk():
            instance = super(CreateAnimLib, self).process()

            self.log.info("Creating AnimLib instance set up ...")
            controls = cmds.sets(name="controls_SET", empty=True)
            # pointcache = cmds.sets(name="out_SET", empty=True)
            cmds.sets([controls, pointcache], forceElement=instance)
