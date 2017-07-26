# absolute_import is needed to counter the `module has no cmds error` in Maya
from __future__ import absolute_import

import os
import uuid

from maya import cmds

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

    To retrieve the invalid nodes this assumes a static `repair(instance)`
    method is available on the plugin.

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

    To retrieve the invalid nodes this assumes a static `repair(instance)`
    method is available on the plugin.

    """
    label = "Repair Context"
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
            plugin.repair()


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

        # Ensure unique (process each node only once)
        invalid = list(set(invalid))

        if invalid:
            self.log.info("Selecting invalid nodes: %s" % ", ".join(invalid))
            cmds.select(invalid, replace=True, noExpand=True)
        else:
            self.log.info("No invalid nodes found.")
            cmds.select(deselect=True)


class GenerateUUIDsOnInvalidAction(pyblish.api.Action):
    """Generate UUIDs on the invalid nodes in the instance.

    Invalid nodes are those returned by the plugin's `get_invalid` method.
    As such it is the plug-in's responsibility to ensure the nodes that
    receive new UUIDs are actually invalid.

    Requires:
        - currentFile on context

    """

    label = "Regenerate UUIDs"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):

        self.log.info("Finding bad nodes..")

        # Get the errored instances
        errored_instances = []
        for result in context.data["results"]:
            if result["error"] is not None and result["instance"] is not None:
                if result["error"]:
                    instance = result["instance"]
                    errored_instances.append(instance)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        # Get the nodes from the all instances that ran through this plug-in
        invalid = []
        for instance in instances:
            invalid_nodes = plugin.get_invalid(instance)
            if invalid_nodes:
                invalid.extend(invalid_nodes)

        if not invalid:
            self.log.info("No invalid nodes found.")
            return

        # Ensure unique (process each node only once)
        invalid = list(set(invalid))

        # Parse context from current file
        self.log.info("Parsing current context..")
        print(">>> DEBUG CONTEXT :", context)
        print(">>> DEBUG CONTEXT DATA:", context.data)

        # # Generate and add the ids to the nodes
        node_ids = self.generate_ids(context, invalid)
        self.apply_ids(node_ids)
        self.log.info("Generated ids on nodes: {0}".format(invalid))

    def get_context(self, instance=None):

        PROJECT = os.environ["AVALON_PROJECT"]
        ASSET = instance.data.get("asset") or os.environ["AVALON_ASSET"]
        SILO = os.environ["AVALON_SILO"]
        LOCATION = os.getenv("AVALON_LOCATION")

        return {"project": PROJECT,
                "asset": ASSET,
                "silo": SILO,
                "location": LOCATION}

    def generate_ids(self, context, nodes):
        """Generate cb UUIDs for nodes.

        The identifiers are formatted like:
            assets:character/test:bluey:46D221D9-4150-8E49-6B17-43B04BFC26B6

        This is a concatenation of:
            - entity (shots or assets)
            - folders (parent hierarchy)
            - asset (the name of the asset)
            - uuid (unique id for node in the scene)

        Raises:
            RuntimeError: When context can't be parsed of the current asset

        Returns:
            dict: node, uuid dictionary

        """

        # Make a copy of the context
        data = context.copy()

        # Define folders

        node_ids = dict()
        for node in nodes:
            # Generate a unique ID per node
            data['uuid'] = uuid.uuid4()
            unique_id = "{asset}:{item}:{uuid}".format(**data)
            node_ids[node] = unique_id

        return node_ids

    def apply_ids(self, node_ids):
        """Apply the created unique IDs to the node
        Args:
            node_ids (dict): each node with a unique id

        Returns:
            None
        """

        attribute = "mbId"
        for node, id in node_ids.items():
            # check if node has attribute
            if not cmds.attributeQuery(attribute, node=node, exists=True):
                cmds.addAttr(node, longName=attribute, dataType="string")

            cmds.setAttr("{}.{}".format(node, attribute), id)
