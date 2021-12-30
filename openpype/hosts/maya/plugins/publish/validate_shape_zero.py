from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib

from avalon.maya import maintained_selection


class ValidateShapeZero(pyblish.api.Validator):
    """shape can't have any values

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
        """Returns the invalid shapes in the instance.

        This is the same as checking:
        - all(pnt == [0,0,0] for pnt in shape.pnts[:])

        Returns:
            list: Shape with non freezed vertex

        """

        shapes = cmds.ls(instance, type="shape")

        invalid = []
        for shape in shapes:
            if cmds.polyCollapseTweaks(shape, q=True, hasVertexTweaks=True):
                invalid.append(shape)

        return invalid

    @classmethod
    def repair(cls, instance):
        invalid_shapes = cls.get_invalid(instance)
        if not invalid_shapes:
            return

        with maintained_selection():
            with lib.tool("selectSuperContext"):
                for shape in invalid_shapes:
                    cmds.polyCollapseTweaks(shape)
                    # cmds.polyCollapseTweaks keeps selecting the geometry
                    # after each command. When running on many meshes
                    # after one another this tends to get really heavy
                    cmds.select(clear=True)

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Nodes found with shape or vertices not freezed"
                             "values: {0}".format(invalid))
