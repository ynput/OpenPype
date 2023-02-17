from openpype.hosts.maya.api import (
    lib,
    plugin
)

from maya import cmds


class CreateArnoldSceneSource(plugin.Creator):
    """Arnold Scene Source"""

    name = "ass"
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

    def __init__(self, *args, **kwargs):
        super(CreateArnoldSceneSource, self).__init__(*args, **kwargs)

        # Add animation data
        self.data.update(lib.collect_animation_data())

        self.data["expandProcedurals"] = self.expandProcedurals
        self.data["motionBlur"] = self.motionBlur
        self.data["motionBlurKeys"] = self.motionBlurKeys
        self.data["motionBlurLength"] = self.motionBlurLength

        # Masks
        self.data["maskOptions"] = self.maskOptions
        self.data["maskCamera"] = self.maskCamera
        self.data["maskLight"] = self.maskLight
        self.data["maskShape"] = self.maskShape
        self.data["maskShader"] = self.maskShader
        self.data["maskOverride"] = self.maskOverride
        self.data["maskDriver"] = self.maskDriver
        self.data["maskFilter"] = self.maskFilter
        self.data["maskColor_manager"] = self.maskColor_manager
        self.data["maskOperator"] = self.maskOperator

    def process(self):
        instance = super(CreateArnoldSceneSource, self).process()

        nodes = []

        if (self.options or {}).get("useSelection"):
            nodes = cmds.ls(selection=True)

        cmds.sets(nodes, rm=instance)

        assContent = cmds.sets(name=instance + "_content_SET")
        assProxy = cmds.sets(name=instance + "_proxy_SET", empty=True)
        cmds.sets([assContent, assProxy], forceElement=instance)
