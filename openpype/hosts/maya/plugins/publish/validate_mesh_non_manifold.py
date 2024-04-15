from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateMeshOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


def _as_report_list(values, prefix="- ", suffix="\n"):
    """Return list as bullet point list for a report"""
    if not values:
        return ""
    return prefix + (suffix + prefix).join(values)


class ValidateMeshNonManifold(pyblish.api.Validator,
                              OptionalPyblishPluginMixin):
    """Ensure that meshes don't have non-manifold edges or vertices

    To debug the problem on the meshes you can use Maya's modeling
    tool: "Mesh > Cleanup..."

    """

    order = ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = 'Mesh Non-Manifold Edges/Vertices'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = True

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type='mesh', long=True)

        invalid = []
        for mesh in meshes:
            if (cmds.polyInfo(mesh, nonManifoldVertices=True) or
                    cmds.polyInfo(mesh, nonManifoldEdges=True)):
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Meshes found with non-manifold edges/vertices:\n\n{0}".format(
                    _as_report_list(sorted(invalid))
                ),
                title="Non-Manifold Edges/Vertices"
            )
