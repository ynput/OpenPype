from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib
from openpype.pipeline.publish import (
    ValidateMeshOrder,
    PublishValidationError
)


class ValidateMeshNgons(pyblish.api.Validator):
    """Ensure that meshes don't have ngons

    Ngon are faces with more than 4 sides.

    To debug the problem on the meshes you can use Maya's modeling
    tool: "Mesh > Cleanup..."

    """

    order = ValidateMeshOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Mesh ngons"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    description = (
        "## Meshes with NGONs Faces\n"
        "Detected meshes with NGON faces. <b>NGONS<b> are faces that "
        "with more than four sides.\n\n"
        "### How to repair?\n"
        "You can repair them by usings Maya's modeling tool Mesh > Cleanup.. "
        "and select to cleanup matching polygons for lamina faces."
    )

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type='mesh', long=True)

        # Get all faces
        faces = ['{0}.f[*]'.format(node) for node in meshes]

        # Filter to n-sided polygon faces (ngons)
        invalid = lib.polyConstraint(faces,
                                     t=0x0008,  # type=face
                                     size=3)    # size=nsided

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Meshes found with n-gons: {0}".format(invalid),
                description=self.description
            )
