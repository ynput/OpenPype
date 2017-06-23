from maya import cmds

import pyblish.api
import colorbleed.api

import cbra.utils.maya.node_uuid as id_utils


def get_id_from_history(node):
    """Return the ID from the first node in the history of the same type

    If the node itself has an ID that will be returned. If no ID found None is
    returned.

    Returns:
        str: The id on first node in history

    """

    nodeType = cmds.nodeType(node)
    history = cmds.listHistory(node, leaf=False) or []
    similar = cmds.ls(history, exactType=nodeType, long=True)

    for node in similar:
        id = id_utils.get_id(node)
        if id:
            return id


class CopyUUIDsFromHistoryAction(pyblish.api.Action):
    """Copy UUIDs from the history of a node.

    This allows a deformed Shape to take its UUID from the original shape.

    """

    label = "Copy UUIDs from History"
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
            invalid.extend(invalid_nodes)

        # Ensure unique
        invalid = list(set(invalid))

        if not invalid:
            self.log.info("No invalid nodes found.")
            return

        # Generate a mapping of UUIDs using history
        mapping = dict()
        for shape in invalid:
            id = get_id_from_history(shape)
            if not id:
                self.log.info("No ID found in history of: {0}".format(shape))
                continue
            mapping[shape] = id

        # Add the ids to the nodes
        id_utils.add_ids(mapping)
        self.log.info("Generated ids on nodes: {0}".format(mapping.values()))


class ValidateLayoutShapeNodeIds(pyblish.api.InstancePlugin):
    """Validate shapes nodes have colorbleed id attributes

    All non-referenced transforms in the hierarchy should have unique IDs.
    This does not check for unique shape ids to allow a same non-referenced
    shape in the output (e.g. when multiple of the same characters are in
    the scene with a deformer on it).

    How?

    This usually happens when a node was created locally and did not come
    from a correctly published asset.

    In the case you're entirely sure you still want to publish the shapes
    you can forcefully generate ids for them. USE WITH CARE! Select the
    nodes (shapes!) and run:
        > scripts > pyblish > utilities > regenerate_uuids

    Why?

    The pipeline needs the ids to be able to identify "what" an object is.
    When it knows that it's able to correctly assign its shaders or do all
    kinds of other magic with it!

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.layout']
    hosts = ['maya']
    label = 'Layout Shape Ids'
    actions = [colorbleed.api.SelectInvalidAction,
               CopyUUIDsFromHistoryAction]

    @staticmethod
    def get_invalid(instance):

        nodes = cmds.ls(instance, shapes=True, long=True)
        referenced = cmds.ls(nodes, referencedNodes=True, long=True)
        non_referenced = set(nodes) - set(referenced)

        # Ignore specific node types
        # `deformFunc` = deformer shapes
        IGNORED = ("gpuCache",
                   "constraint",
                   "lattice",
                   "baseLattice",
                   "geometryFilter",
                   "deformFunc",
                   "locator")

        ignored_nodes = cmds.ls(list(non_referenced), type=IGNORED, long=True)
        if ignored_nodes:
            non_referenced -= set(ignored_nodes)

        invalid = []
        for node in non_referenced:
            if not id_utils.get_id(node):
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Shapes (non-referenced) found in layout "
                               "without asset IDs: {0}".format(invalid))
