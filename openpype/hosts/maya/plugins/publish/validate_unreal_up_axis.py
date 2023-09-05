# -*- coding: utf-8 -*-

import pyblish.api
from maya import cmds

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    RepairAction,
    ValidateContentsOrder,
)


class ValidateUnrealUpAxis(pyblish.api.ContextPlugin,
                           OptionalPyblishPluginMixin):
    """Validate if Z is set as up axis in Maya"""

    optional = True
    active = False
    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["staticMesh"]
    label = "Unreal Up-Axis check"
    actions = [RepairAction]

    def process(self, context):
        if not self.is_active(context.data):
            return

        assert cmds.upAxis(q=True, axis=True) == "z", (
            "Invalid axis set as up axis"
        )

    @classmethod
    def repair(cls, instance):
        cmds.upAxis(axis="z", rotateView=True)
