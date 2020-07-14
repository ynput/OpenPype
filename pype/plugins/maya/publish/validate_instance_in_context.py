# -*- coding: utf-8 -*-
"""Validate if instance asset is the same as context asset."""
from __future__ import absolute_import
import pyblish.api
from pype.action import get_errored_instances_from_context
import pype.api


class SelectInvalidInstances(pyblish.api.Action):
    """Select invalid instances in Outliner."""

    label = "Show Instances"
    icon = "briefcase"
    on = "failed"

    def process(self, context, plugin):
        """Process invalid validators and select invalid instances."""
        try:
            from maya import cmds
        except ImportError:
            raise ImportError("Current host is not Maya")

        errored_instances = get_errored_instances_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid = list()
        for instance in instances:
            invalid_instances = plugin.get_invalid(context)
            if invalid_instances:
                if isinstance(invalid_instances, (list, tuple)):
                    invalid.extend(invalid_instances)
                else:
                    self.log.warning("Plug-in returned to be invalid, "
                                     "but has no selectable nodes.")

        # Ensure unique (process each node only once)
        invalid = list(set(invalid))

        if invalid:
            self.log.info("Selecting invalid nodes: %s" % ", ".join(invalid))
            cmds.select(invalid, replace=True, noExpand=True)
        else:
            self.log.info("No invalid nodes found.")
            cmds.select(deselect=True)


class ValidateInstanceInContext(pyblish.api.ContextPlugin):
    """Validator to check if instance asset match context asset.

    When working in per-shot style you always publish data in context of
    current asset (shot). This validator checks if this is so. It is optional
    so it can be disabled when needed.

    Action on this validator will select invalid instances in Outliner.
    """

    order = pype.api.ValidateContentsOrder
    label = "Instance in same Context"
    optional = True
    actions = [SelectInvalidInstances]

    @classmethod
    def get_invalid(cls, context):
        """Get invalid instances."""
        invalid = []
        context_asset = context.data["assetEntity"]["name"]
        cls.log.info("we are in {}".format(context_asset))
        for instance in context:
            asset = instance.data.get("asset")
            if asset != context_asset:
                cls.log.warning("{} has asset {}".format(instance.name, asset))
                invalid.append(instance.name)

        return invalid

    def process(self, context):
        """Check instances."""
        invalid = self.get_invalid(context)
        if invalid:
            raise AssertionError("Some instances doesn't share same context")
