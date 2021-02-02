# -*- coding: utf-8 -*-

from maya import cmds
import pyblish.api
import pype.api


class ValidateUnrealUpAxis(pyblish.api.ContextPlugin):
    """Validate if Z is set as up axis in Maya"""

    optional = True
    order = pype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["unrealStaticMesh"]
    label = "Unreal Up-Axis check"
    actions = [pype.api.RepairAction]

    def process(self, context):
        assert cmds.upAxis(q=True, axis=True) == "z", (
            "Invalid axis set as up axis"
        )

    @classmethod
    def repair(cls, instance):
        cmds.upAxis(axis="z", rotateView=True)
