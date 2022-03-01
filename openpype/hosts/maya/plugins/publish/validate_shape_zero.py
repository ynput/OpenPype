from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib


class ValidateShapeZero(pyblish.api.Validator):
    """Shape components may not have any "tweak" values

    To solve this issue, try freezing the shapes.

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

        with lib.maintained_selection():
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
            raise ValueError("Shapes found with non-zero component tweaks: "
                             "{0}".format(invalid))
