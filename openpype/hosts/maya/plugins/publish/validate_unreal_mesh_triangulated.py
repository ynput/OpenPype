# -*- coding: utf-8 -*-

from maya import cmds
import pyblish.api

from openpype.pipeline.publish import (
    ValidateMeshOrder,
    PublishValidationError
)
import openpype.hosts.maya.api.action


class ValidateUnrealMeshTriangulated(pyblish.api.InstancePlugin):
    """Validate if mesh is made of triangles for Unreal Engine"""

    order = ValidateMeshOrder
    hosts = ["maya"]
    families = ["staticMesh"]
    label = "Mesh is Triangulated"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    active = False

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        meshes = cmds.ls(instance, type="mesh", long=True)
        for mesh in meshes:
            faces = cmds.polyEvaluate(mesh, face=True)
            tris = cmds.polyEvaluate(mesh, triangle=True)
            if faces != tris:
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Found meshes without triangles")
