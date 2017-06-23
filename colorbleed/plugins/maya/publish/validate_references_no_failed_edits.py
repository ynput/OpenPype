import pyblish.api
import colorbleed.api
from maya import cmds



class RepairFailedEditsAction(pyblish.api.Action):
    label = "Remove failed edits"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):
        from maya import cmds
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
            invalid.extend(invalid_nodes)

        if not invalid:
            self.log.info("No invalid nodes found.")
            return

        for ref in invalid:
            self.log.info("Remove failed edits for: {0}".format(ref))
            cmds.referenceEdit(ref,
                               removeEdits=True,
                               failedEdits=True,
                               successfulEdits=False)
        self.log.info("Removed failed edits")


class ValidateReferencesNoFailedEdits(pyblish.api.InstancePlugin):
    """Validate that all referenced nodes' reference nodes don't have failed
    reference edits.

    Failed reference edits can happen if you apply a change to a referenced
    object in the scene and then change the source of the reference
    (referenced file) to remove the object. The reference edit can't be
    applied to the node because it is missing, hence a "failed edit". This
    could unnecessarily bloat file sizes and degrade load/save speed.

    To investigate reference edits you can "List edits" on a reference
    and look for those edits that appear as failed. Usually failed edits
    are near the bottom of the list.

    """

    order = colorbleed.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['colorbleed.layout']
    category = 'layout'
    optional = True
    version = (0, 1, 0)
    label = 'References Failed Edits'
    actions = [colorbleed.api.SelectInvalidAction,
               RepairFailedEditsAction]

    @staticmethod
    def get_invalid(instance):
        """Return invalid reference nodes in the instance

        Terminology:
            reference node: The node that is the actual reference containing
                the nodes (type: reference)
            referenced nodes: The nodes contained within the reference
                (type: any type of nodes)

        """
        referenced_nodes = cmds.ls(instance, referencedNodes=True, long=True)
        if not referenced_nodes:
            return list()

        # Get reference nodes from referenced nodes
        # (note that reference_nodes != referenced_nodes)
        reference_nodes = set()
        for node in referenced_nodes:
            reference_node = cmds.referenceQuery(node, referenceNode=True)
            if reference_node:
                reference_nodes.add(reference_node)

        # Check for failed edits on each reference node.
        invalid = []
        for reference_node in reference_nodes:
            failed_edits = cmds.referenceQuery(reference_node,
                                               editNodes=True,
                                               failedEdits=True,
                                               successfulEdits=False)
            if failed_edits:
                invalid.append(reference_node)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Reference nodes found with failed "
                             "reference edits: {0}".format(invalid))
