import pyblish.api

from avalon.nuke.lib import (
    reset_selection,
    select_nodes
)

from ...action import get_errored_instances_from_context


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid nodes in Nuke when plug-in failed.

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """
    label = "Select invalid nodes"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):

        try:
            import nuke
        except ImportError:
            raise ImportError("Current host is not Nuke")

        errored_instances = get_errored_instances_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid = list()
        for instance in instances:
            invalid_nodes = plugin.get_invalid(instance)

            if invalid_nodes:
                if isinstance(invalid_nodes, (list, tuple)):
                    invalid.append(invalid_nodes[0])
                else:
                    self.log.warning("Plug-in returned to be invalid, "
                                     "but has no selectable nodes.")

        # Ensure unique (process each node only once)
        invalid = list(set(invalid))

        if invalid:
            self.log.info("Selecting invalid nodes: {}".format(invalid))
            reset_selection()
            select_nodes(invalid)
        else:
            self.log.info("No invalid nodes found.")
