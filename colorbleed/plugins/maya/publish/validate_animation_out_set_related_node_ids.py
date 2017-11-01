import maya.cmds as cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


def get_parent(node):
    """Get the parent node of the given node
    Args:
        node (str): full path of the node

    Returns:
        str, full path if parent node
    """
    return cmds.listRelatives(node, parent=True, fullPath=True)


class ValidateOutRelatedNodeIds(pyblish.api.InstancePlugin):
    """Validate if nodes have related IDs to the source (original shapes)

    Any intermediate shapes which are created when creating deformers on
    shapes will need to get the correct ID to ensure the look assignment still
    works on the new shape.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.animation', "colorbleed.pointcache"]
    hosts = ['maya']
    label = 'Animation Out Set Related Node Ids'
    actions = [colorbleed.api.SelectInvalidAction, colorbleed.api.RepairAction]
    optional = True

    ignore_types = ("constraint",)

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

        # get asset id
        nodes = instance.data.get("out_hierarchy", instance[:])
        for node in nodes:
            # check if node is a shape as deformers only work on shapes
            obj_type = cmds.objectType(node, isAType="shape")
            node_id = lib.get_id(node)

            if obj_type and not node_id:
                invalid.append(node)
                continue

            if not node_id:
                continue

            root_id = cls.get_history_root_id(node=node)
            if root_id is not None:
                invalid.append(node)

        return invalid

    @classmethod
    def get_history_root_id(cls, node):
        """
        Get the original node ID when a node has been deformed

        Args:
            node (str): node to retrieve the

        Returns:
            str: the asset ID as found in the database

        """

        node = cmds.ls(node, long=True)[0]

        # We only check when the node is *not* referenced
        if cmds.referenceQuery(node, isNodeReferenced=True):
            return

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

    @classmethod
    def repair(cls, instance):

        for node in cls.get_invalid(instance):
            # Get root asset ID
            root_id = cls.get_history_root_id(node=node)
            if not root_id:
                cls.log.error("Could not find root ID for '%s'", node)
                continue

            cmds.setAttr("%s.cbId" % node, root_id, type="string")
