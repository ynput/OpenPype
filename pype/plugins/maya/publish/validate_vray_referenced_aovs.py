# -*- coding: utf-8 -*-
"""Validate if there are AOVs pulled from references."""
import pyblish.api
import pype.api

from maya import cmds

import pype.hosts.maya.action


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
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    def process(self, instance):
        """Plugin main entry point."""
        if instance.data.get("renderer") != "vray":
            # If not V-Ray ignore..
            return

        if not instance.data.get("vrayUseReferencedAovs"):
            self.get_invalid(instance)

    @classmethod
    def get_invalid(cls, instance):
        """Find referenced AOVs in scene."""

        if cmds.getAttr("vraySettings.relements_usereferenced") == 0:
            ref_aovs = cmds.ls(
                type=["VRayRenderElement", "VRayRenderElementSet"],
                referencedNodes=True) or []

        if ref_aovs:
            cls.log.warning(
                "Scene contain referenced AOVs: {}".format(ref_aovs))

            # Return the instance itself
            return ref_aovs
