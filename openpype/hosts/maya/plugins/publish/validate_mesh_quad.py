from maya import cmds, mel

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from avalon import maya
from openpype.hosts.maya.api import lib

def polySelectConstraint(objects, *args, **kwargs):

    kwargs['mode'] = kwargs.get('mode') or 2

    with lib.no_undo(flush=False):
        with maya.maintained_selection():
            with lib.reset_polySelectConstraint():
                cmds.select(objects, r=1, noExpand=True)
                cmds.polySelectConstraint(*args, **kwargs)
                result = cmds.ls(selection=True)
                cmds.select(clear=True)
    return result

class ValidateMeshQuad(pyblish.api.Validator):
    """Mesh should not contain ngones (face with more than 4 vertices)

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Mesh quads"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        """Returns the invalid transforms in the instance.

        Returns:
            list: Meshes with ngons

        """

        # Acting as polyCleanupArgList n-sided polygons selection
        meshes = cmds.ls(instance, type='mesh')
        return polySelectConstraint(meshes, m=3, t=8, sz=3)


    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Nodes found with shape or vertices not freezed "
                             "values: {0}".format(invalid))
