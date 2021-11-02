from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from avalon import maya
from openpype.hosts.maya.api import lib


def polyConstraint(objects, *args, **kwargs):
    kwargs.pop('mode', None)

    with lib.no_undo(flush=False):
        with maya.maintained_selection():
            with lib.reset_polySelectConstraint():
                cmds.select(objects, r=1, noExpand=True)
                # Acting as 'polyCleanupArgList' for n-sided polygon selection
                cmds.polySelectConstraint(*args, mode=3, **kwargs)
                result = cmds.ls(selection=True)
                cmds.select(clear=True)

    return result


class ValidateMeshNgons(pyblish.api.Validator):
    """Ensure that meshes don't have ngons

    Ngon are faces with more than 4 sides.

    To debug the problem on the meshes you can use Maya's modeling
    tool: "Mesh > Cleanup..."

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Mesh ngons"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type='mesh')
        return polyConstraint(meshes, type=8, size=3)

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Meshes found with n-gons"
                             "values: {0}".format(invalid))
