from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib


class ValidateNodeIdsDeformedShape(pyblish.api.InstancePlugin):
    """Validate if deformed shapes have related IDs to the original shapes.

    When a deformer is applied in the scene on a referenced mesh that already
    had deformers then Maya will create a new shape node for the mesh that
    does not have the original id. This validator checks whether the ids are
    valid on all the shape nodes in the instance.

    """

    order = openpype.api.ValidateContentsOrder
    families = ['look']
    hosts = ['maya']
    label = 'Deformed shape ids'
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction,
        openpype.api.RepairAction
    ]

    def process(self, instance):
        """Process all the nodes in the instance"""

        # Ensure all nodes have a cbId and a related ID to the original shapes
        # if a deformer has been created on the shape
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Shapes found that are considered 'Deformed'"
                               "without object ids: {0}".format(invalid))

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
            history_id = lib.get_id_from_sibling(shape)
            if history_id:
                current_id = lib.get_id(shape)
                if current_id != history_id:
                    invalid.append(shape)

        return invalid

    @classmethod
    def repair(cls, instance):

        for node in cls.get_invalid(instance):
            # Get the original id from history
            history_id = lib.get_id_from_sibling(node)
            if not history_id:
                cls.log.error("Could not find ID in history for '%s'", node)
                continue

            lib.set_id(node, history_id, overwrite=True)
