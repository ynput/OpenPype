from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import (
    NumberDef,
    BoolDef
)



class CreateArnoldSceneSource(plugin.MayaCreator):
    """Arnold Scene Source"""

    identifier = "io.openpype.creators.maya.ass"
    label = "Arnold Scene Source"
    family = "ass"
    icon = "cube"

    expandProcedurals = False
    motionBlur = True
    motionBlurKeys = 2
    motionBlurLength = 0.5
    maskOptions = False
    maskCamera = False
    maskLight = False
    maskShape = False
    maskShader = False
    maskOverride = False
    maskDriver = False
    maskFilter = False
    maskColor_manager = False
    maskOperator = False

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()

        defs.extend([
            BoolDef("expandProcedural",
                    label="Expand Procedural",
                    default=self.expandProcedurals),
            BoolDef("motionBlur",
                    label="Motion Blur",
                    default=self.motionBlur),
            NumberDef("motionBlurKeys",
                      label="Motion Blur Keys",
                      decimals=0,
                      default=self.motionBlurKeys),
            NumberDef("motionBlurLength",
                      label="Motion Blur Length",
                      decimals=3,
                      default=self.motionBlurLength),

            # Masks
            BoolDef("maskOptions",
                    label="Mask Options",
                    default=self.maskOptions),
            BoolDef("maskCamera",
                    label="Mask Camera",
                    default=self.maskCamera),
            BoolDef("maskLight",
                    label="Mask Light",
                    default=self.maskLight),
            BoolDef("maskShape",
                    label="Mask Shape",
                    default=self.maskShape),
            BoolDef("maskShader",
                    label="Mask Shader",
                    default=self.maskShader),
            BoolDef("maskOverride",
                    label="Mask Override",
                    default=self.maskOverride),
            BoolDef("maskDriver",
                    label="Mask Driver",
                    default=self.maskDriver),
            BoolDef("maskFilter",
                    label="Mask Filter",
                    default=self.maskFilter),
            BoolDef("maskColor_manager",
                    label="Mask Color Manager",
                    default=self.maskColor_manager),
            BoolDef("maskOperator",
                    label="Mask Operator",
                    default=self.maskOperator),
        ])

        return defs

    def create(self, subset_name, instance_data, pre_create_data):

        from maya import cmds

        instance = super(CreateArnoldSceneSource, self).create(
            subset_name, instance_data, pre_create_data
        )

        instance_node = instance.get("instance_node")

        content = cmds.sets(name=instance_node + "_content_SET", empty=True)
        proxy = cmds.sets(name=instance_node + "_proxy_SET", empty=True)
        cmds.sets([content, proxy], forceElement=instance)
