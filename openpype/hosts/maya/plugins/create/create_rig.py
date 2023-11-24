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
        # TODO：change name (_controls_SET -> _rigs_SET)
        controls = cmds.sets(name=subset_name + "_controls_SET", empty=True)
        # TODO：change name (_out_SET -> _geo_SET)
        pointcache = cmds.sets(name=subset_name + "_out_SET", empty=True)
        skeleton = cmds.sets(
            name=subset_name + "_skeletonAnim_SET", empty=True)
        skeleton_mesh = cmds.sets(
            name=subset_name + "_skeletonMesh_SET", empty=True)
        cmds.sets([controls, pointcache,
                   skeleton, skeleton_mesh], forceElement=instance_node)
