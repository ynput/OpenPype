from maya import cmds

import pyblish.api

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateRigJointsHidden(pyblish.api.InstancePlugin):
    """Validate all joints are hidden visually.

    This includes being hidden:
        - visibility off,
        - in a display layer that has visibility off,
        - having hidden parents or
        - being an intermediate object.

    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ['rig']
    label = "Joints Hidden"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               RepairAction]

    @staticmethod
    def get_invalid(instance):
        joints = cmds.ls(instance, type='joint', long=True)
        return [j for j in joints if lib.is_visible(j, displayLayer=True)]

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Visible joints found: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        import maya.mel as mel
        mel.eval("HideJoints")
