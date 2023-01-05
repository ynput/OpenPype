# absolute_import is needed to counter the `module has no cmds error` in Maya
from __future__ import absolute_import

import pyblish.api


def get_errored_instances_from_context(context):

    instances = list()
    for result in context.data["results"]:
        if result["instance"] is None:
            # When instance is None we are on the "context" result
            continue

        if result["error"]:
            instances.append(result["instance"])

    return instances


def get_errored_plugins_from_data(context):
    """Get all failed validation plugins

    Args:
        context (object):

    Returns:
        list of plugins which failed during validation

    """

    plugins = list()
    results = context.data.get("results", [])
    for result in results:
        if result["success"] is True:
            continue
        plugins.append(result["plugin"])

    return plugins


class RepairAction(pyblish.api.Action):
    """Repairs the action

    To process the repairing this requires a static `repair(instance)` method
    is available on the plugin.

    """
    label = "Repair"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):

        if not hasattr(plugin, "repair"):
            raise RuntimeError("Plug-in does not have repair method.")

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_instances = get_errored_instances_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)
        for instance in instances:
            plugin.repair(instance)


class RepairContextAction(pyblish.api.Action):
    """Repairs the action

    To process the repairing this requires a static `repair(instance)` method
    is available on the plugin.

    """
    label = "Repair"
    on = "failed"  # This action is only available on a failed plug-in

    def process(self, context, plugin):

        if not hasattr(plugin, "repair"):
            raise RuntimeError("Plug-in does not have repair method.")

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_plugins = get_errored_plugins_from_data(context)

        # Apply pyblish.logic to get the instances for the plug-in
        if plugin in errored_plugins:
            self.log.info("Attempting fix ...")
            plugin.repair(context)
