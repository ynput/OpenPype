from maya import cmds

from openpype.hosts.maya.api import plugin


class CreateRig(plugin.MayaCreator):
    """Artist-friendly rig with controls to direct motion"""

    identifier = "io.openpype.creators.maya.rig"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"

    def create(self, subset_name, instance_data, pre_create_data):

        instance = super(CreateRig, self).create(subset_name,
                                                 instance_data,
                                                 pre_create_data)

        instance_node = instance.get("instance_node")

        self.log.info("Creating Rig instance set up ...")
        controls = cmds.sets(name="controls_SET", empty=True)
        pointcache = cmds.sets(name="out_SET", empty=True)
        cmds.sets([controls, pointcache], forceElement=instance_node)
