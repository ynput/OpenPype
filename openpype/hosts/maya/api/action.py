# absolute_import is needed to counter the `module has no cmds error` in Maya
from __future__ import absolute_import

import pyblish.api

from openpype.pipeline import legacy_io
from openpype.api import get_errored_instances_from_context


class GenerateUUIDsOnInvalidAction(pyblish.api.Action):
    """Generate UUIDs on the invalid nodes in the instance.

    Invalid nodes are those returned by the plugin's `get_invalid` method.
    As such it is the plug-in's responsibility to ensure the nodes that
    receive new UUIDs are actually invalid.

    Requires:
        - instance.data["asset"]

    """

    label = "Regenerate UUIDs"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):

        from maya import cmds

        self.log.info("Finding bad nodes..")

        errored_instances = get_errored_instances_from_context(context)

        # Apply pyblish logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        # Get the nodes from the all instances that ran through this plug-in
        all_invalid = []
        for instance in instances:
            invalid = plugin.get_invalid(instance)

            # Don't allow referenced nodes to get their ids regenerated to
            # avoid loaded content getting messed up with reference edits
            if invalid:
                referenced = {node for node in invalid if
                              cmds.referenceQuery(node, isNodeReferenced=True)}
                if referenced:
                    self.log.warning("Skipping UUID generation on referenced "
                                     "nodes: {}".format(list(referenced)))
                    invalid = [node for node in invalid
                               if node not in referenced]

            if invalid:

                self.log.info("Fixing instance {}".format(instance.name))
                self._update_id_attribute(instance, invalid)

                all_invalid.extend(invalid)

        if not all_invalid:
            self.log.info("No invalid nodes found.")
            return

        all_invalid = list(set(all_invalid))
        self.log.info("Generated ids on nodes: {0}".format(all_invalid))

    def _update_id_attribute(self, instance, nodes):
        """Delete the id attribute

        Args:
            instance: The instance we're fixing for
            nodes (list): all nodes to regenerate ids on
        """

        from . import lib

        asset = instance.data['asset']
        asset_id = legacy_io.find_one(
            {"name": asset, "type": "asset"},
            projection={"_id": True}
        )['_id']
        for node, _id in lib.generate_ids(nodes, asset_id=asset_id):
            lib.set_id(node, _id, overwrite=True)


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid nodes in Maya when plug-in failed.

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """
    label = "Select invalid"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):

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
            invalid_nodes = plugin.get_invalid(instance)
            if invalid_nodes:
                if isinstance(invalid_nodes, (list, tuple)):
                    invalid.extend(invalid_nodes)
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
