# -*- coding: utf-8 -*-
"""Validate if instance asset is the same as context asset."""
from __future__ import absolute_import

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)

from maya import cmds


class ValidateInstanceInContext(pyblish.api.InstancePlugin,
                                OptionalPyblishPluginMixin):
    """Validator to check if instance asset match context asset and task.

    When working in per-shot style you always publish data in context of
    current asset (shot) and task. This validator checks if this is so. It is
    optional so it can be disabled when needed.

    Action on this validator will select invalid instances in Outliner.
    """

    # Depends on CollectContextEntities
    order = ValidateContentsOrder
    label = "Instance in same Context"
    optional = True
    hosts = ["maya"]
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction, RepairAction
    ]

    def process(self, instance):
        if not self.is_active(instance.data):
            return


        message = (
            "Instance '{}' publishes to a different {} than current context: "
            "{}. Current context: {}"
        )
        description = (
            "## Publishing to a different asset or task\n"
            "There are publish instances present which are publishing into a "
            "different asset or task than your current context.\n\n"
            "Usually this is not what you want but there can be cases where "
            "you might want to publish into another asset or shot. If that's "
            "the case you can disable the validation on the instance to "
            "ignore it."
        )

        # Validate asset context.
        asset = instance.data.get("asset")
        context_asset = self.get_context_asset(instance)
        if asset != instance.context.data["assetEntity"]["name"]:
            raise PublishValidationError(
                message=message.format(
                    instance.name, "asset", asset, context_asset
                ),
                description=description
            )

        # Validate task context.
        if instance.context.data["task"] != instance.data["task"]:
            raise PublishValidationError(
                message=message.format(
                    instance.name,
                    "task",
                    instance.data["task"],
                    instance.context.data["task"]
                ),
                description=description
            )

    @classmethod
    def get_invalid(cls, instance):
        return [instance.data["instance_node"]]

    @classmethod
    def repair(cls, instance):
        context_asset = cls.get_context_asset(instance)
        instance_node = instance.data["instance_node"]
        cmds.setAttr(
            "{}.asset".format(instance_node),
            context_asset,
            type="string"
        )
        cmds.setAttr(
            "{}.task".format(instance_node),
            instance.context.data["task"],
            type="string"
        )

    @staticmethod
    def get_context_asset(instance):
        return instance.context.data["assetEntity"]["name"]
