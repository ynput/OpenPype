
from maya import cmds

import pyblish.api
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder
)


class ValidateGLSLPlugin(pyblish.api.InstancePlugin):
    """
    Validate if the asset uses GLSL Shader
    """

    order = ValidateContentsOrder + 0.15
    families = ['gltf']
    hosts = ['maya']
    label = 'maya2glTF plugin'
    actions = [RepairAction]

    def process(self, instance):
        if not cmds.pluginInfo("maya2glTF", query=True, loaded=True):
            raise RuntimeError("maya2glTF is not loaded")

    @classmethod
    def repair(cls, instance):
        """
        Repair instance by enabling the plugin
        """
        return cmds.loadPlugin("maya2glTF", quiet=True)
