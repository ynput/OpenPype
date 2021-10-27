from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action


class ValidateShapeZero(pyblish.api.Validator):
    """shape and shape's vertex can't have any values

    To solve this issue, try freezing the shapes. So long
    as the translation, rotation and scaling values are zero,
    you're all good.

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Shape Zero (Freeze)"
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction,
        openpype.api.RepairAction
    ]

    @staticmethod
    def get_invalid(instance):
        """Returns invalid shapes with non-freezed vertex.

        Returns:
            list: shapes with non-freezed vertex

        """

        shapes = cmds.ls(instance, type="shape")

        invalid = []
        for shape in shapes:
            if cmds.polyCollapseTweaks(shape, query=True, hasVertexTweaks=True):
                invalid.append(shape)

        return invalid

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for i in invalid:
            cmds.polyCollapseTweaks(i)

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Nodes found with shape or vertices not freezed "
                             "values: {0}".format(invalid))
