import maya.cmds as cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib


class ValidateRigOutSetNodeIds(pyblish.api.InstancePlugin):
    """Validate if deformed shapes have related IDs to the original shapes.

    When a deformer is applied in the scene on a referenced mesh that already
    had deformers then Maya will create a new shape node for the mesh that
    does not have the original id. This validator checks whether the ids are
    valid on all the shape nodes in the instance.

    """

    order = openpype.api.ValidateContentsOrder
    families = ["rig"]
    hosts = ['maya']
    label = 'Rig Out Set Node Ids'
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction,
        openpype.api.RepairAction
    ]
    allow_history_only = False

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId and a related ID to the original shapes
        # if a deformer has been created on the shape
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found with mismatching "
                               "IDs: {0}".format(invalid))

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
            sibling_id = lib.get_id_from_sibling(
                shape,
                history_only=cls.allow_history_only
            )
            if sibling_id:
                current_id = lib.get_id(shape)
                if current_id != sibling_id:
                    invalid.append(shape)

        return invalid

    @classmethod
    def repair(cls, instance):

        for node in cls.get_invalid(instance):
            # Get the original id from sibling
            sibling_id = lib.get_id_from_sibling(
                node,
                history_only=cls.allow_history_only
            )
            if not sibling_id:
                cls.log.error("Could not find ID in siblings for '%s'", node)
                continue

            lib.set_id(node, sibling_id, overwrite=True)
