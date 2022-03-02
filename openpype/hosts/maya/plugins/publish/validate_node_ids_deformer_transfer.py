from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib


class ValidateNodeIdsDeformerTransfer(pyblish.api.InstancePlugin):
    """Validate if deformed shapes have related IDs to the original
    shapes.

    When a deformer is applied in the scene on a mesh,
    Maya creates a new "deformer" shape node for the mesh.
    This new node does not get the original ID and later references
    to the original node ID don't match.

    This validator checks whether the IDs are valid on all the shape
    nodes in the instance.
    """

    order = openpype.api.ValidateContentsOrder
    families = ['rig']
    hosts = ['maya']
    label = 'Deformed shape ids transferred'
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction,
        openpype.api.RepairAction
    ]

    def process(self, instance):
        """Process all the nodes in the instance"""

        # Ensure nodes with sibling share the same ID
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Shapes found that are considered 'Deformed'"
                " with invalid object ids: {0}".format(invalid)
            )

    @classmethod
    def get_invalid(cls, instance):
        """Get all nodes which do not match the criteria"""

        shapes = cmds.ls(instance[:],
                         dag=True,
                         leaf=True,
                         shapes=True,
                         long=True,
                         noIntermediate=True)

        invalid = []
        for shape in shapes:
            sibling_id = cls._get_id_from_sibling(shape)
            if not sibling_id:
                continue

            current_id = lib.get_id(shape)
            if current_id != sibling_id:
                invalid.append(shape)

        return invalid

    @classmethod
    def _get_id_from_sibling(cls, node):
        """In some cases, the history of the deformed shapes cannot be used
        to get the original shape, as the relation with the orignal shape
        has been lost.
        The original shape can be found as a sibling of the deformed shape
        (sharing same transform parent), which has the "intermediate object"
        attribute set.
        The ID of that shape node can then be transferred to the deformed
        shape node.
        """

        # Get long name
        node = cmds.ls(node, long=True)[0]

        parent = cmds.listRelatives(node, parent=True, fullPath=True)

        # Get siblings of same type
        node_type = cmds.nodeType(node)
        similar_nodes = cmds.listRelatives(parent, type=node_type, fullPath=1)
        # Exclude itself
        similar_nodes = [x for x in similar_nodes if x != node]

        for similar_node in similar_nodes:
            # Make sure it is an "intermediate object"
            if cmds.getAttr(similar_node + ".io"):
                _id = lib.get_id(similar_node)
                if _id:
                    return _id

    @classmethod
    def repair(cls, instance):

        for node in cls.get_invalid(instance):
            # Get the original id from sibling
            sibling_id = cls._get_id_from_sibling(node)
            if not sibling_id:
                cls.log.error("Could not find ID from sibling for '%s'", node)
                continue

            lib.set_id(node, sibling_id, overwrite=True)
