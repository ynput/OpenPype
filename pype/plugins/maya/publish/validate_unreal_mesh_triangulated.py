# -*- coding: utf-8 -*-

from maya import cmds
import pyblish.api
import pype.api


class ValidateUnrealMeshTriangulated(pyblish.api.InstancePlugin):
    """Validate if mesh is made of triangles for Unreal Engine"""

    order = pype.api.ValidateMeshOder
    hosts = ["maya"]
    families = ["unrealStaticMesh"]
    category = "geometry"
    label = "Mesh is Triangulated"
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        meshes = cmds.ls(instance, type="mesh", long=True)
        for mesh in meshes:
            faces = cmds.polyEvaluate(mesh, f=True)
            tris = cmds.polyEvaluate(mesh, t=True)
            if faces != tris:
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        assert len(invalid) == 0, (
            "Found meshes without triangles")
