import pyblish.api
import hou

from openpype.pipeline.publish import get_errored_instances_from_context


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid nodes in Maya when plug-in failed.

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """
    label = "Select invalid"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):

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
                    invalid.extend(invalid_nodes)
                else:
                    self.log.warning("Plug-in returned to be invalid, "
                                     "but has no selectable nodes.")

        hou.clearAllSelected()
        if invalid:
            self.log.info("Selecting invalid nodes: {}".format(
                ", ".join(node.path() for node in invalid)
            ))
            for node in invalid:
                node.setSelected(True)
                node.setCurrent(True)
        else:
            self.log.info("No invalid nodes found.")


class SelectROPAction(pyblish.api.Action):
    """Select ROP.

    It's used to select the associated ROPs with all errored instances
    not necessarily the ones that errored on the plugin we're running the action on.
    """

    label = "Select ROP"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "mdi.cursor-default-click"

    def process(self, context, plugin):
        errored_instances = get_errored_instances_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding ROP nodes..")
        rop_nodes = list()
        for instance in instances:
            node_path = instance.data.get("instance_node")
            if not node_path:
                continue

            node = hou.node(node_path)
            if not node:
                continue

            rop_nodes.append(node)

        hou.clearAllSelected()
        if rop_nodes:
            self.log.info("Selecting ROP nodes: {}".format(
                ", ".join(node.path() for node in rop_nodes)
            ))
            for node in rop_nodes:
                node.setSelected(True)
                node.setCurrent(True)
        else:
            self.log.info("No ROP nodes found.")
