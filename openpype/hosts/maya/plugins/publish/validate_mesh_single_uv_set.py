from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib
from openpype.pipeline.publish import (
    RepairAction,
    ValidateMeshOrder,
    OptionalPyblishPluginMixin
)


class ValidateMeshSingleUVSet(pyblish.api.InstancePlugin,
                              OptionalPyblishPluginMixin):
    """Warn on multiple UV sets existing for each polygon mesh.

    On versions prior to Maya 2017 this will force no multiple uv sets because
    the Alembic exports in Maya prior to 2017 don't support writing multiple
    UV sets.

    """

    order = ValidateMeshOrder
    hosts = ['maya']
    families = ['model', 'pointcache']
    optional = True
    label = "Mesh Single UV Set"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               RepairAction]

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type='mesh', long=True)

        invalid = []
        for mesh in meshes:
            uvSets = cmds.polyUVSet(mesh,
                                    query=True,
                                    allUVSets=True) or []

            # ensure unique (sometimes maya will list 'map1' twice)
            uvSets = set(uvSets)

            if len(uvSets) != 1:
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.warning(
                "Meshes found with multiple UV sets: {0}".format(invalid)
            )

    @classmethod
    def repair(cls, instance):
        for mesh in cls.get_invalid(instance):
            lib.remove_other_uv_sets(mesh)
