# -*- coding: utf-8 -*-
"""Validate if instance asset is the same as context asset."""
from __future__ import absolute_import

import nuke

import pyblish.api
import openpype.api
from openpype.hosts.nuke.api.lib import (
    recreate_instance,
    reset_selection,
    select_nodes
)


class SelectInvalidInstances(pyblish.api.Action):
    """Select invalid instances in Outliner."""

    label = "Select Instances"
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
        select_nodes(
            [nuke.toNode(str(x)) for x in instances]
        )

    def deselect(self):
        reset_selection()


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

        context_asset = context.data["assetEntity"]["name"]
        for instance in instances:
            origin_node = instance[0]
            recreate_instance(
                origin_node, avalon_data={"asset": context_asset}
            )


class ValidateInstanceInContext(pyblish.api.InstancePlugin):
    """Validator to check if instance asset match context asset.

    When working in per-shot style you always publish data in context of
    current asset (shot). This validator checks if this is so. It is optional
    so it can be disabled when needed.

    Action on this validator will select invalid instances in Outliner.
    """

    order = openpype.api.ValidateContentsOrder
    label = "Instance in same Context"
    hosts = ["nuke"]
    actions = [SelectInvalidInstances, RepairSelectInvalidInstances]
    optional = True

    def process(self, instance):
        asset = instance.data.get("asset")
        context_asset = instance.context.data["assetEntity"]["name"]
        msg = "{} has asset {}".format(instance.name, asset)
        assert asset == context_asset, msg
