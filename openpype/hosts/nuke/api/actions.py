import pyblish.api

from openpype.pipeline.publish import get_errored_instances_from_context
from .lib import (
    reset_selection,
    select_nodes
)


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid nodes in Nuke when plug-in failed.

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """
    label = "Select invalid nodes"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):

        # Get the errored instances for the plug-in
        errored_instances = get_errored_instances_from_context(
            context, plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid_nodes = set()
        for instance in errored_instances:
            invalid = plugin.get_invalid(instance)

            if not invalid:
                continue

            select_node = instance.data.get("transientData", {}).get("node")
            if not select_node:
                raise RuntimeError(
                    "No transientData['node'] found on instance: {}".format(
                        instance)
                )

            invalid_nodes.add(select_node)

        if invalid_nodes:
            self.log.info("Selecting invalid nodes: {}".format(invalid_nodes))
            reset_selection()
            select_nodes(list(invalid_nodes))
        else:
            self.log.info("No invalid nodes found.")
