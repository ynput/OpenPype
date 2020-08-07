from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateMeshNormalsUnlocked(pyblish.api.Validator):
    """Validate all meshes in the instance have unlocked normals

    These can be unlocked manually through:
        Modeling > Mesh Display > Unlock Normals

    """

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    category = 'geometry'
    version = (0, 1, 0)
    label = 'Mesh Normals Unlocked'
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]
    optional = True

    @staticmethod
    def has_locked_normals(mesh):
        """Return whether a mesh node has locked normals"""
        return any(cmds.polyNormalPerVertex("{}.vtxFace[*][*]".format(mesh),
                                            query=True,
                                            freezeNormal=True))

    @classmethod
    def get_invalid(cls, instance):
        """Return the meshes with locked normals in instance"""

        meshes = cmds.ls(instance, type='mesh', long=True)
        return [mesh for mesh in meshes if cls.has_locked_normals(mesh)]

    def process(self, instance):
        """Raise invalid when any of the meshes have locked normals"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Meshes found with "
                             "locked normals: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        """Unlocks all normals on the meshes in this instance."""
        invalid = cls.get_invalid(instance)
        for mesh in invalid:
            cmds.polyNormalPerVertex(mesh, unFreezeNormal=True)
