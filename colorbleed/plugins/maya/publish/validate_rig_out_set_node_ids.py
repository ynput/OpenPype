import maya.cmds as cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


def get_id_from_history(node):
    """Return first node id in the history chain that matches this node.

    The nodes in history must be of the exact same node type and must be
    parented under the same parent.

    Args:
        node (str): node to retrieve the

    Returns:
        str or None: The id from the node in history or None when no id found
            on any valid nodes in the history.

    """

    node = cmds.ls(node, long=True)[0]

    # Find all similar nodes in history
    history = cmds.listHistory(node)
    node_type = cmds.nodeType(node)
    similar_nodes = cmds.ls(history, exactType=node_type, long=True)

    # Exclude itself
    similar_nodes = [x for x in similar_nodes if x != node]

    # The node *must be* under the same parent
    parent = get_parent(node)
    similar_nodes = [i for i in similar_nodes if
                     get_parent(i) == parent]

    # Check all of the remaining similar nodes and take the first one
    # with an id and assume it's the original.
    for similar_node in similar_nodes:
        _id = lib.get_id(similar_node)
        if _id:
            return _id


def get_parent(node):
    """Get the parent node of the given node
    Args:
        node (str): full path of the node

    Returns:
        str, full path if parent node
    """
    return cmds.listRelatives(node, parent=True, fullPath=True)


class ValidateRigOutSetNodeIds(pyblish.api.InstancePlugin):
    """Validate if deformed shapes have related IDs to the original shapes.

    When a deformer is applied in the scene on a referenced mesh that already
    had deformers then Maya will create a new shape node for the mesh that
    does not have the original id. This validator checks whether the ids are
    valid on all the shape nodes in the instance.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ["colorbleed.rig"]
    hosts = ['maya']
    label = 'Rig Out Set Node Ids'
    actions = [colorbleed.api.SelectInvalidAction, colorbleed.api.RepairAction]

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId and a related ID to the original shapes
        # if a deformer has been created on the shape
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found with non-related "
                               "asset IDs: {0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):
        """Get all nodes which do not match the criteria"""

        invalid = []

        out_set = next(x for x in instance if x.endswith("out_SET"))
        members = cmds.sets(out_set, query=True)
        shapes = cmds.ls(members,
                         dag=True,
                         leaf=True,
                         shapes=True,
                         long=True,
                         noIntermediate=True)

        for shape in shapes:
            history_id = get_id_from_history(shape)
            if history_id:
                current_id = lib.get_id(shape)
                if current_id != history_id:
                    invalid.append(shape)

        return invalid

    @classmethod
    def repair(cls, instance):

        for node in cls.get_invalid(instance):
            # Get the original id from history
            history_id = get_id_from_history(node)
            if not history_id:
                cls.log.error("Could not find ID in history for '%s'", node)
                continue

            lib.set_id(node, history_id, overwrite=True)
