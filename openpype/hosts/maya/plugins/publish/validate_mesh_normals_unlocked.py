from maya import cmds
import maya.api.OpenMaya as om2

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action


class ValidateMeshNormalsUnlocked(pyblish.api.Validator):
    """Validate all meshes in the instance have unlocked normals

    These can be unlocked manually through:
        Modeling > Mesh Display > Unlock Normals

    """

    order = openpype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    category = 'geometry'
    version = (0, 1, 0)
    label = 'Mesh Normals Unlocked'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               openpype.api.RepairAction]
    optional = True

    @staticmethod
    def has_locked_normals(mesh):
        """Return whether mesh has at least one locked normal"""

        sel = om2.MGlobal.getSelectionListByName(mesh)
        node = sel.getDependNode(0)
        fn_mesh = om2.MFnMesh(node)
        _, normal_ids = fn_mesh.getNormalIds()
        for normal_id in normal_ids:
            if fn_mesh.isNormalLocked(normal_id):
                return True
        return False

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
