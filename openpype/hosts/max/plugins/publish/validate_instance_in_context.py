# -*- coding: utf-8 -*-
"""Validate if instance asset is the same as context asset."""
from __future__ import absolute_import

import pyblish.api
from openpype import AYON_SERVER_ENABLED
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.max.api.action import SelectInvalidAction
from pymxs import runtime as rt


class ValidateInstanceInContext(pyblish.api.InstancePlugin,
                                OptionalPyblishPluginMixin):
    """Validator to check if instance asset match context asset.

    When working in per-shot style you always publish data in context of
    current asset (shot). This validator checks if this is so. It is optional
    so it can be disabled when needed.

    Action on this validator will select invalid instances.
    """

    order = ValidateContentsOrder
    label = "Instance in same Context"
    optional = True
    hosts = ["max"]
    actions = [SelectInvalidAction, RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        instance_node = rt.getNodeByName(instance.data.get(
            "instance_node", ""))
        if not instance_node:
            return
        asset_name_attr = "folderPath" if AYON_SERVER_ENABLED else "asset"
        asset = rt.getUserProp(instance_node, asset_name_attr)
        context_asset = self.get_context_asset(instance)
        task = rt.getUserProp(instance_node, "task")
        context_task = self.get_context_task(instance)
        if asset != context_asset:
            raise PublishValidationError(
                message=(
                    "Instance '{}' publishes to different asset than current "
                    "context: {}. Current context: {}".format(
                        instance.name, asset, context_asset
                    )
                ),
                description=(
                    "## Publishing to a different asset\n"
                    "There are publish instances present which are publishing "
                    "into a different asset than your current context.\n\n"
                    "Usually this is not what you want but there can be cases "
                    "where you might want to publish into another asset or "
                    "shot. If that's the case you can disable the validation "
                    "on the instance to ignore it."
                )
            )
        if task != context_task:
            raise PublishValidationError(
                message=(
                    "Instance '{}' publishes to different task than current "
                    "context: {}. Current context: {}".format(
                        instance.name, task, context_task
                    )
                ),
                description=(
                    "## Publishing to a different asset\n"
                    "There are publish instances present which are publishing "
                    "into a different asset than your current context.\n\n"
                    "Usually this is not what you want but there can be cases "
                    "where you might want to publish into another asset or "
                    "shot. If that's the case you can disable the validation "
                    "on the instance to ignore it."
                )
            )

    @classmethod
    def get_invalid(cls, instance):
        asset_name_attr = "folderPath" if AYON_SERVER_ENABLED else "asset"
        node = rt.getNodeByName(instance.data["instance_node"])
        asset = rt.getUserProp(node, asset_name_attr)
        context_asset = cls.get_context_asset(instance)
        if asset != context_asset:
            return instance.data["instance_node"]

    @classmethod
    def repair(cls, instance):
        context_asset = cls.get_context_asset(instance)
        context_task = cls.get_context_task(instance)
        instance_node = rt.getNodeByName(instance.data.get(
            "instance_node", ""))
        if not instance_node:
            return
        asset_name_attr = "folderPath" if AYON_SERVER_ENABLED else "asset"
        rt.SetUserProp(instance_node, asset_name_attr, context_asset)
        rt.SetUserProp(instance_node, "task", context_task)

    @staticmethod
    def get_context_asset(instance):
        return instance.context.data["asset"]

    @staticmethod
    def get_context_task(instance):
        return instance.context.data["task"]
