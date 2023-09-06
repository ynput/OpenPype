import maya.cmds as cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
)


def has_shape_children(node):
    # Check if any descendants
    allDescendents = cmds.listRelatives(node,
                                        allDescendents=True,
                                        fullPath=True)
    if not allDescendents:
        return False

    # Check if there are any shapes at all
    shapes = cmds.ls(allDescendents, shapes=True)
    if not shapes:
        return False

    # Check if all descendent shapes are intermediateObjects;
    # if so we consider this node a null node and return False.
    if all(cmds.getAttr('{0}.intermediateObject'.format(x)) for x in shapes):
        return False

    return True


class ValidateNoNullTransforms(pyblish.api.InstancePlugin):
    """Ensure no null transforms are in the scene.

    Warning:
        Transforms with only intermediate shapes are also considered null
        transforms. These transform nodes could potentially be used in your
        construction history, so take care when automatically fixing this or
        when deleting the empty transforms manually.

    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ['model']
    label = 'No Empty/Null Transforms'
    actions = [RepairAction,
               openpype.hosts.maya.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):
        """Return invalid transforms in instance"""

        transforms = cmds.ls(instance, type='transform', long=True)

        invalid = []
        for transform in transforms:
            if not has_shape_children(transform):
                invalid.append(transform)

        return invalid

    def process(self, instance):
        """Process all the transform nodes in the instance """
        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Empty transforms found: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        """Delete all null transforms.

        Note: If the node is used elsewhere (eg. connection to attributes or
        in history) deletion might mess up things.

        """
        invalid = cls.get_invalid(instance)
        if invalid:
            cmds.delete(invalid)
