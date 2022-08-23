# -*- coding: utf-8 -*-
"""Validate if there are AOVs pulled from references."""
import pyblish.api
import types
from maya import cmds

import openpype.hosts.maya.api.action


class ValidateVrayReferencedAOVs(pyblish.api.InstancePlugin):
    """Validate whether the V-Ray Render Elements (AOVs) include references.

    This will check if there are AOVs pulled from references. If
    `Vray Use Referenced Aovs` is checked on render instance, u must add those
    manually to Render Elements as Pype will expect them to be rendered.

    """

    order = pyblish.api.ValidatorOrder
    label = 'VRay Referenced AOVs'
    hosts = ['maya']
    families = ['renderlayer']
    actions = [openpype.api.RepairContextAction]

    def process(self, instance):
        """Plugin main entry point."""
        if instance.data.get("renderer") != "vray":
            # If not V-Ray ignore..
            return

        ref_aovs = cmds.ls(
            type=["VRayRenderElement", "VRayRenderElementSet"],
            referencedNodes=True)
        ref_aovs_enabled = ValidateVrayReferencedAOVs.maya_is_true(
            cmds.getAttr("vraySettings.relements_usereferenced"))

        if not instance.data.get("vrayUseReferencedAovs"):
            if ref_aovs_enabled and ref_aovs:
                self.log.warning((
                    "Referenced AOVs are enabled in Vray "
                    "Render Settings and are detected in scene, but "
                    "Pype render instance option for referenced AOVs is "
                    "disabled. Those AOVs will be rendered but not published "
                    "by Pype."
                ))
                self.log.warning(", ".join(ref_aovs))
        else:
            if not ref_aovs:
                self.log.warning((
                    "Use of referenced AOVs enabled but there are none "
                    "in the scene."
                ))
            if not ref_aovs_enabled:
                self.log.error((
                    "'Use referenced' not enabled in Vray Render Settings."
                ))
                raise AssertionError("Invalid render settings")

    @classmethod
    def repair(cls, context):
        """Repair action."""
        vray_settings = cmds.ls(type="VRaySettingsNode")
        if not vray_settings:
            node = cmds.createNode("VRaySettingsNode")
        else:
            node = vray_settings[0]

        cmds.setAttr("{}.relements_usereferenced".format(node), True)

    @staticmethod
    def maya_is_true(attr_val):
        """Whether a Maya attr evaluates to True.

        When querying an attribute value from an ambiguous object the
        Maya API will return a list of values, which need to be properly
        handled to evaluate properly.

        Args:
            attr_val (mixed): Maya attribute to be evaluated as bool.

        Returns:
            bool: cast Maya attribute to Pythons boolean value.

        """
        if isinstance(attr_val, bool):
            return attr_val
        elif isinstance(attr_val, (list, types.GeneratorType)):
            return any(attr_val)
        else:
            return bool(attr_val)
