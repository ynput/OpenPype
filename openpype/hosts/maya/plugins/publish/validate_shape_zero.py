from maya import cmds

import pyblish.api

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateShapeZero(pyblish.api.Validator,
                        OptionalPyblishPluginMixin):
    """Shape components may not have any "tweak" values

    To solve this issue, try freezing the shapes.

    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Shape Zero (Freeze)"
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction,
        RepairAction
    ]
    optional = True

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
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                title="Shape Component Tweaks",
                message="Shapes found with non-zero component tweaks: '{}'"
                        "".format(", ".join(invalid)),
                description=(
                    "## Shapes found with component tweaks\n"
                    "Shapes were detected that have component tweaks on their "
                    "components. Please remove the component tweaks to "
                    "continue.\n\n"
                    "### Repair\n"
                    "The repair action will try to *freeze* the component "
                    "tweaks into the shapes, which is usually the correct fix "
                    "if the mesh has no construction history (= has its "
                    "history deleted)."),
                detail=(
                    "Maya allows to store component tweaks within shape nodes "
                    "which are applied between its `inMesh` and `outMesh` "
                    "connections resulting in the output of a shape node "
                    "differing from the input. We usually want to avoid this "
                    "for published meshes (in particular for Maya scenes) as "
                    "it can have unintended results when using these meshes "
                    "as intermediate meshes since it applies positional "
                    "differences without being visible edits in the node "
                    "graph.\n\n"
                    "These tweaks are traditionally stored in the `.pnts` "
                    "attribute of shapes.")
            )
