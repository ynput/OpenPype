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

        errored_instances = get_errored_instances_from_context(context,
                                                               plugin=plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid = set()
        for instance in errored_instances:
            invalid_nodes = plugin.get_invalid(instance)

            if invalid_nodes:
                if isinstance(invalid_nodes, (list, tuple)):
                    invalid.update(invalid_nodes)
                else:
                    self.log.warning("Plug-in returned to be invalid, "
                                     "but has no selectable nodes.")

        if invalid:
            self.log.info("Selecting invalid nodes: {}".format(invalid))
            reset_selection()
            select_nodes(invalid)
        else:
            self.log.info("No invalid nodes found.")


class SelectInstanceNodeAction(pyblish.api.Action):
    """Select instance node for failed plugin."""
    label = "Select instance node"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "mdi.cursor-default-click"

    def process(self, context, plugin):

        # Get the errored instances for the plug-in
        errored_instances = get_errored_instances_from_context(
            context, plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding instance nodes..")
        nodes = set()
        for instance in errored_instances:
            instance_node = instance.data.get("transientData", {}).get("node")
            if not instance_node:
                raise RuntimeError(
                    "No transientData['node'] found on instance: {}".format(
                        instance
                    )
                )
            nodes.add(instance_node)

        if nodes:
            self.log.info("Selecting instance nodes: {}".format(nodes))
            reset_selection()
            select_nodes(nodes)
        else:
            self.log.info("No instance nodes found.")
