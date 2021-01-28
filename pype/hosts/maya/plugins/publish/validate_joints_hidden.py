from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action
from pype.hosts.maya import lib


class ValidateJointsHidden(pyblish.api.InstancePlugin):
    """Validate all joints are hidden visually.

    This includes being hidden:
        - visibility off,
        - in a display layer that has visibility off,
        - having hidden parents or
        - being an intermediate object.

    """

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['rig']
    category = 'rig'
    version = (0, 1, 0)
    label = "Joints Hidden"
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]

    @staticmethod
    def get_invalid(instance):
        joints = cmds.ls(instance, type='joint', long=True)
        return [j for j in joints if lib.is_visible(j, displayLayer=True)]

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""
        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Visible joints found: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        import maya.mel as mel
        mel.eval("HideJoints")
