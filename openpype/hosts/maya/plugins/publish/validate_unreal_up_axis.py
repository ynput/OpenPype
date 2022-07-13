# -*- coding: utf-8 -*-

from maya import cmds
import pyblish.api
import openpype.api


class ValidateUnrealUpAxis(pyblish.api.ContextPlugin):
    """Validate if Z is set as up axis in Maya"""

    optional = True
    active = False
    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["staticMesh"]
    label = "Unreal Up-Axis check"
    actions = [openpype.api.RepairAction]

    def process(self, context):
        assert cmds.upAxis(q=True, axis=True) == "z", (
            "Invalid axis set as up axis"
        )

    @classmethod
    def repair(cls, instance):
        cmds.upAxis(axis="z", rotateView=True)
