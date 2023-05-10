# -*- coding: utf-8 -*-
"""Validate if instance asset is the same as context asset."""
from __future__ import absolute_import

import pyblish.api

import openpype.hosts.nuke.api.lib as nlib

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)

class SelectInvalidInstances(pyblish.api.Action):
    """Select invalid instances in Outliner."""

    label = "Select"
    icon = "briefcase"
    on = "failed"

    def process(self, context, plugin):
        """Process invalid validators and select invalid instances."""
        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (
                result["error"] is None
                or result["instance"] is None
                or result["instance"] in failed
                or result["plugin"] != plugin
            ):
                continue

            failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)

        if instances:
            self.deselect()
            self.log.info(
                "Selecting invalid nodes: %s" % ", ".join(
                    [str(x) for x in instances]
                )
            )
            self.select(instances)
        else:
            self.log.info("No invalid nodes found.")
            self.deselect()

    def select(self, instances):
        for inst in instances:
            if inst.data.get("transientData", {}).get("node"):
                select_node = inst.data["transientData"]["node"]
                select_node["selected"].setValue(True)

    def deselect(self):
        nlib.reset_selection()


class RepairSelectInvalidInstances(pyblish.api.Action):
    """Repair the instance asset."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (
                result["error"] is None
                or result["instance"] is None
                or result["instance"] in failed
                or result["plugin"] != plugin
            ):
                continue

            failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)
        self.log.debug(instances)

        context_asset = context.data["assetEntity"]["name"]
        for instance in instances:
            node = instance.data["transientData"]["node"]
            node_data = nlib.get_node_data(node, nlib.INSTANCE_DATA_KNOB)
            node_data["asset"] = context_asset
            nlib.set_node_data(node, nlib.INSTANCE_DATA_KNOB, node_data)


class ValidateCorrectAssetName(
    pyblish.api.InstancePlugin,
    OptionalPyblishPluginMixin
):
    """Validator to check if instance asset match context asset.

    When working in per-shot style you always publish data in context of
    current asset (shot). This validator checks if this is so. It is optional
    so it can be disabled when needed.

    Action on this validator will select invalid instances in Outliner.
    """
    order = ValidateContentsOrder
    label = "Validate correct asset name"
    hosts = ["nuke"]
    actions = [
        SelectInvalidInstances,
        RepairSelectInvalidInstances
    ]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        asset = instance.data.get("asset")
        context_asset = instance.context.data["assetEntity"]["name"]
        node = instance.data["transientData"]["node"]

        msg = (
            "Instance `{}` has wrong shot/asset name:\n"
            "Correct: `{}` | Wrong: `{}`").format(
                instance.name, asset, context_asset)

        self.log.debug(msg)

        if asset != context_asset:
            raise PublishXmlValidationError(
                self, msg, formatting_data={
                    "node_name": node.name(),
                    "wrong_name": asset,
                    "correct_name": context_asset
                }
            )
