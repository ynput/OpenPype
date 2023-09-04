from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateMeshOrder,
    PublishValidationError
)


class ValidateMeshLaminaFaces(pyblish.api.InstancePlugin):
    """Validate meshes don't have lamina faces.

    Lamina faces share all of their edges.

    """

    order = ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = 'Mesh Lamina Faces'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    description = (
        "## Meshes with Lamina Faces\n"
        "Detected meshes with lamina faces. <b>Lamina faces</b> are faces "
        "that share all of their edges and thus are merged together on top of "
        "each other.\n\n"
        "### How to repair?\n"
        "You can repair them by using Maya's modeling tool `Mesh > Cleanup..` "
        "and select to cleanup matching polygons for lamina faces."
    )

    @staticmethod
    def get_invalid(instance):
        meshes = cmds.ls(instance, type='mesh', long=True)
        invalid = [mesh for mesh in meshes if
                   cmds.polyInfo(mesh, laminaFaces=True)]

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Meshes found with lamina faces: {0}".format(invalid),
                description=self.description
            )
