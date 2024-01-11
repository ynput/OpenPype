# -*- coding: utf-8 -*-
"""Validator for correct naming of Static Meshes."""
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
)
from openpype.hosts.houdini.api.action import SelectInvalidAction
from openpype.pipeline.create import get_subset_name

import hou


class FixSubsetNameAction(RepairAction):
    label = "Fix Subset Name"


class ValidateSubsetName(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validate Subset name.

    """

    families = ["staticMesh"]
    hosts = ["houdini"]
    label = "Validate Subset Name"
    order = ValidateContentsOrder + 0.1
    actions = [FixSubsetNameAction, SelectInvalidAction]

    optional = True

    def process(self, instance):

        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.path() for n in invalid]
            raise PublishValidationError(
                "See log for details. "
                "Invalid nodes: {0}".format(nodes)
            )

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        rop_node = hou.node(instance.data["instance_node"])

        # Check subset name
        asset_doc = instance.data["assetEntity"]
        subset_name = get_subset_name(
            family=instance.data["family"],
            variant=instance.data["variant"],
            task_name=instance.data["task"],
            asset_doc=asset_doc,
            dynamic_data={"asset": asset_doc["name"]}
        )

        if instance.data.get("subset") != subset_name:
            invalid.append(rop_node)
            cls.log.error(
                "Invalid subset name on rop node '%s' should be '%s'.",
                rop_node.path(), subset_name
            )

        return invalid

    @classmethod
    def repair(cls, instance):
        rop_node = hou.node(instance.data["instance_node"])

        # Check subset name
        asset_doc = instance.data["assetEntity"]
        subset_name = get_subset_name(
            family=instance.data["family"],
            variant=instance.data["variant"],
            task_name=instance.data["task"],
            asset_doc=asset_doc,
            dynamic_data={"asset": asset_doc["name"]}
        )

        instance.data["subset"] = subset_name
        rop_node.parm("subset").set(subset_name)

        cls.log.debug(
            "Subset name on rop node '%s' has been set to '%s'.",
            rop_node.path(), subset_name
        )
