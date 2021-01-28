from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateColorSets(pyblish.api.Validator):
    """Validate all meshes in the instance have unlocked normals

    These can be removed manually through:
        Modeling > Mesh Display > Color Sets Editor

    """

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    category = 'geometry'
    label = 'Mesh ColorSets'
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]
    optional = True

    @staticmethod
    def has_color_sets(mesh):
        """Return whether a mesh node has locked normals"""
        return cmds.polyColorSet(mesh,
                                 allColorSets=True,
                                 query=True)

    @classmethod
    def get_invalid(cls, instance):
        """Return the meshes with ColorSets in instance"""

        meshes = cmds.ls(instance, type='mesh', long=True)
        return [mesh for mesh in meshes if cls.has_color_sets(mesh)]

    def process(self, instance):
        """Raise invalid when any of the meshes have ColorSets"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Meshes found with "
                             "Color Sets: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        """Remove all Color Sets on the meshes in this instance."""
        invalid = cls.get_invalid(instance)
        for mesh in invalid:
            for set in cmds.polyColorSet(mesh, acs=True, q=True):
                cmds.polyColorSet(mesh, colorSet=set, delete=True)
