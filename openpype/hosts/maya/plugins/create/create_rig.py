from maya import cmds

from openpype.hosts.maya.api import plugin
from openpype.lib import BoolDef


class CreateRig(plugin.MayaCreator):
    """Artist-friendly rig with controls to direct motion"""

    identifier = "io.openpype.creators.maya.rig"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data["fbx_enabled"] = pre_create_data.get("fbx_enabled")

        instance = super(CreateRig, self).create(subset_name,
                                                 instance_data,
                                                 pre_create_data)

        instance_node = instance.get("instance_node")

        self.log.info("Creating Rig instance set up ...")
        # change name
        controls = cmds.sets(name=subset_name + "_controls_SET", empty=True)
        # change name
        pointcache = cmds.sets(name=subset_name + "_out_SET", empty=True)
        if pre_create_data.get("fbx_enabled"):
            skeleton = cmds.sets(
                name=subset_name + "_skeleton_SET", empty=True)
            skeleton_mesh = cmds.sets(
                name=subset_name + "_skeletonMesh_SET", empty=True)
            cmds.sets([controls, pointcache,
                       skeleton, skeleton_mesh], forceElement=instance_node)
        else:
            cmds.sets([controls, pointcache], forceElement=instance_node)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateRig, self).get_pre_create_attr_defs()

        return attrs + [
            BoolDef("fbx_enabled",
                    label="Fbx Export",
                    default=False),

        ]
