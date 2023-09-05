import pyblish.api
from maya import cmds

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib
from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateMeshOrder,
)


class ValidateMeshNonZeroEdgeLength(pyblish.api.InstancePlugin,
                                    OptionalPyblishPluginMixin):
    """Validate meshes don't have edges with a zero length.

    Based on Maya's polyCleanup 'Edges with zero length'.

    Note:
        This can be slow for high-res meshes.

    """

    order = ValidateMeshOrder
    families = ['model']
    hosts = ['maya']
    label = 'Mesh Edge Length Non Zero'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = True

    __tolerance = 1e-5

    @classmethod
    def get_invalid(cls, instance):
        """Return the invalid edges.

        Also see:

        http://help.autodesk.com/view/MAYAUL/2015/ENU/?guid=Mesh__Cleanup

        """

        meshes = cmds.ls(instance, type='mesh', long=True)
        if not meshes:
            return list()

        valid_meshes = []
        for mesh in meshes:
            num_vertices = cmds.polyEvaluate(mesh, vertex=True)

            if num_vertices == 0:
                cls.log.warning(
                    "Skipping \"{}\", cause it does not have any "
                    "vertices.".format(mesh)
                )
                continue

            valid_meshes.append(mesh)

        # Get all edges
        edges = ['{0}.e[*]'.format(node) for node in valid_meshes]

        # Filter by constraint on edge length
        invalid = lib.polyConstraint(edges,
                                     t=0x8000,  # type=edge
                                     length=1,
                                     lengthbound=(0, cls.__tolerance))

        return invalid

    def process(self, instance):
        """Process all meshes"""
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            label = "Meshes found with zero edge length"
            raise PublishValidationError(
                message="{}: {}".format(label, invalid),
                title=label,
                description="{}:\n- ".format(label) + "\n- ".join(invalid)
            )
