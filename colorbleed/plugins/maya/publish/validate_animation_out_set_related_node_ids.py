import maya.cmds as cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateAnimationOutSetRelatedNodeIds(pyblish.api.InstancePlugin):
    """Validate if nodes have related IDs to the source (original shapes)

    An ID is 'related' if its built in the current Item.

    Note that this doesn't ensure it's from the current Task. An ID created
    from `lookdev` has the same relation to the Item as one coming from others,
    like `rigging` or `modeling`.

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
        nodes = instance.data["pointcache_data"]
        for node in nodes:
            node_type = cmds.nodeType(node)
            node_id = lib.get_id(node)

            if node_type == "mesh" and not node_id:
                invalid.append(node)
                continue

            if not node_id:
                continue

            root_id = cls.get_history_root_id(node=node)
            if root_id is not None:
                asset_id = cls.to_item(node_id)
                if root_id != asset_id:
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

        asset_id = None
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
        parent = cls.get_parent(node)
        similar_nodes = [i for i in similar_nodes if
                         cls.get_parent(i) == parent]

        # Check all of the remaining similar nodes and take the first one
        # with an id and assume it's the original.
        for similar_node in similar_nodes:

            _id = lib.get_id(similar_node)
            if not _id:
                continue

            asset_id = cls.to_item(_id)
            break

        return asset_id

    @classmethod
    def repair(cls, instance):

        for node in cls.get_invalid(instance):
            # Get node ID and the asset ID part
            node_id = lib.get_id(node)
            asset_id = cls.to_item(node_id)

            # Get root asset ID
            root_id = cls.get_history_root_id(node=node)

            # Replace errored ID with good ID
            new_id = node_id.replace(asset_id, root_id)

            cmds.setAttr("%s.cbId" % node, new_id, type="string")

    @staticmethod
    def to_item(_id):
        """Split the item id part from a node id"""
        return _id.split(":", 1)[0]

    @staticmethod
    def get_parent(node):
        return cmds.listRelatives(node, parent=True, fullPath=True)