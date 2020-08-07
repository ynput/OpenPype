import maya.cmds as cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action
from pype.hosts.maya import lib


class ValidateOutRelatedNodeIds(pyblish.api.InstancePlugin):
    """Validate if deformed shapes have related IDs to the original shapes

    When a deformer is applied in the scene on a referenced mesh that already
    had deformers then Maya will create a new shape node for the mesh that
    does not have the original id. This validator checks whether the ids are
    valid on all the shape nodes in the instance.

    """

    order = pype.api.ValidateContentsOrder
    families = ['animation', "pointcache"]
    hosts = ['maya']
    label = 'Animation Out Set Related Node Ids'
    actions = [pype.hosts.maya.action.SelectInvalidAction, pype.api.RepairAction]

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
        types_to_skip = ["locator"]

        # get asset id
        nodes = instance.data.get("out_hierarchy", instance[:])
        for node in nodes:

            # We only check when the node is *not* referenced
            if cmds.referenceQuery(node, isNodeReferenced=True):
                continue

            # Check if node is a shape as deformers only work on shapes
            obj_type = cmds.objectType(node, isAType="shape")
            if not obj_type:
                continue

            # Skip specific types
            if cmds.objectType(node) in types_to_skip:
                continue

            # Get the current id of the node
            node_id = lib.get_id(node)
            if not node_id:
                invalid.append(node)
                continue

            history_id = lib.get_id_from_history(node)
            if history_id is not None and node_id != history_id:
                invalid.append(node)

        return invalid

    @classmethod
    def repair(cls, instance):

        for node in cls.get_invalid(instance):
            # Get the original id from history
            history_id = lib.get_id_from_history(node)
            if not history_id:
                cls.log.error("Could not find ID in history for '%s'", node)
                continue

            lib.set_id(node, history_id, overwrite=True)
