from maya import cmds

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
    settings_name = "CreateAss"

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
                    label="Export Options",
                    default=self.maskOptions),
            BoolDef("maskCamera",
                    label="Export Cameras",
                    default=self.maskCamera),
            BoolDef("maskLight",
                    label="Export Lights",
                    default=self.maskLight),
            BoolDef("maskShape",
                    label="Export Shapes",
                    default=self.maskShape),
            BoolDef("maskShader",
                    label="Export Shaders",
                    default=self.maskShader),
            BoolDef("maskOverride",
                    label="Export Override Nodes",
                    default=self.maskOverride),
            BoolDef("maskDriver",
                    label="Export Drivers",
                    default=self.maskDriver),
            BoolDef("maskFilter",
                    label="Export Filters",
                    default=self.maskFilter),
            BoolDef("maskOperator",
                    label="Export Operators",
                    default=self.maskOperator),
            BoolDef("maskColor_manager",
                    label="Export Color Managers",
                    default=self.maskColor_manager),
        ])

        return defs


class CreateArnoldSceneSourceProxy(CreateArnoldSceneSource):
    """Arnold Scene Source Proxy

    This product type facilitates working with proxy geometry in the viewport.
    """

    identifier = "io.openpype.creators.maya.assproxy"
    label = "Arnold Scene Source Proxy"
    family = "assProxy"
    icon = "cube"

    def create(self, subset_name, instance_data, pre_create_data):
        instance = super(CreateArnoldSceneSource, self).create(
            subset_name, instance_data, pre_create_data
        )

        instance_node = instance.get("instance_node")

        proxy = cmds.sets(name=instance_node + "_proxy_SET", empty=True)
        cmds.sets([proxy], forceElement=instance_node)
