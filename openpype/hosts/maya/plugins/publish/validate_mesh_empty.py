from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    RepairAction,
    ValidateMeshOrder,
    PublishValidationError
)


class ValidateMeshEmpty(pyblish.api.InstancePlugin):
    """Validate meshes have some vertices.

    Its possible to have meshes without any vertices. To replicate
    this issue, delete all faces/polygons then all edges.
    """

    order = ValidateMeshOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Mesh Empty"
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction, RepairAction
    ]

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for node in invalid:
            cmds.delete(node)

    @classmethod
    def get_invalid(cls, instance):
        invalid = []

        meshes = cmds.ls(instance, type="mesh", long=True)
        for mesh in meshes:
            num_vertices = cmds.polyEvaluate(mesh, vertex=True)

            if num_vertices == 0:
                cls.log.warning(
                    "\"{}\" does not have any vertices.".format(mesh)
                )
                invalid.append(mesh)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Meshes found without any vertices: {}".format(invalid)
            )
