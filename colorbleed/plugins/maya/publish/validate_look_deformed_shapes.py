from maya import cmds

import pyblish.api
import colorbleed.api

from cbra.utils.maya.node_uuid import get_id, add_ids


def get_deformed_history_id_mapping(shapes):
    """Return the id from history for nodes that are "Deformed".

    When shapes are referenced and get deformed by a deformer
    the shape is duplicated *without its attributes* as such
    the new shape misses object ids. This method will try to
    trace back in the history to find the first shape with
    ids to identify the possible best match.

    Args:
        shapes (list): The shapes that are deformed.

    Returns:
        dict: Mapping of deformed shape to history shape.

    """

    shapes = cmds.ls(shapes, shapes=True, long=True)

    # Possibly deformed shapes
    deformed_shapes = [x for x in shapes if "Deformed" in x.rsplit("|", 1)[-1]]

    # The deformed shape should not be referenced
    is_referenced = lambda n: cmds.referenceQuery(n, isNodeReferenced=True)
    deformed_shapes = [x for x in deformed_shapes if not is_referenced(x)]

    # Shapes without id
    deformed_shapes_without_id = [x for x in deformed_shapes if not get_id(x)]

    mapping = {}
    for shape in deformed_shapes_without_id:

        node_type = cmds.objectType(shape)
        history = cmds.listHistory(shape)[1:]  # history, skipping itself
        history_shapes = cmds.ls(history, exactType=node_type, long=True)
        if not history_shapes:
            continue

        for history_shape in history_shapes:
            id = get_id(history_shape)
            if not id:
                continue

            mapping[shape] = history_shape
            break

    return mapping


class CopyUUIDsFromHistory(pyblish.api.Action):
    """Repairs the action

    To retrieve the invalid nodes this assumes a static `repair(instance)`
    method is available on the plugin.

    """
    label = "Copy UUIDs from History"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored = colorbleed.api.get_errored_instances_from_context(context)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored, plugin)

        ids_map = dict()
        for instance in instances:
            invalid = plugin.get_invalid(instance)
            mapping = get_deformed_history_id_mapping(invalid)

            for destination, source in mapping.items():
                ids_map[destination] = get_id(source)

        if not ids_map:
            return
        add_ids(ids_map)


class ValidateLookDeformedShapes(pyblish.api.InstancePlugin):
    """Validate look textures are set to ignore color space when set to RAW

    Whenever the format is NOT set to sRGB for a file texture it must have
    its ignore color space file rules checkbox enabled to avoid unwanted
    reverting to sRGB settings upon file relinking.

    To fix this use the select invalid action to find the invalid file nodes
    and then check the "Ignore Color Space File Rules" checkbox under the
    Color Space settings.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look deformed shapes'
    actions = [colorbleed.api.SelectInvalidAction, CopyUUIDsFromHistory]

    @classmethod
    def get_invalid(cls, instance):

        context = instance.context
        nodes = context.data.get("instancePerItemNodesWithoutId", None)
        if not nodes:
            return list()

        mapping = get_deformed_history_id_mapping(nodes)
        return mapping.keys()

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Shapes found that are considered 'Deformed'"
                               "without object ids: {0}".format(invalid))
