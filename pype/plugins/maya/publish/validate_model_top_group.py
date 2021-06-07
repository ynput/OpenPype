# -*- coding: utf-8 -*-
"""Validate if model content has single top group.

This was splitted from `validate_model_content` by client request.

Todo:
    It would be better handle it back in the single validator using Settings.

Deprecated since 2.18

"""
from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateModelTopGroup(pyblish.api.InstancePlugin):
    """Validate if model has only one top group."""

    order = pype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Model Top Group"
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        content_instance = instance.data.get("setMembers", None)
        if not content_instance:
            cls.log.error("Instance has no nodes!")
            return True

        # Top group
        assemblies = cmds.ls(content_instance, assemblies=True, long=True)
        if len(assemblies) != 1:
            cls.log.error("Must have exactly one top group")
            if len(assemblies) == 0:
                cls.log.warning("No top group found. "
                                "(Are there objects in the instance?"
                                " Or is it parented in another group?)")
            return assemblies or True

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Model content is invalid. See log.")
