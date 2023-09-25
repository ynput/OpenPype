import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder
)
from maya import cmds


class ValidateAnimatedReferenceRig(pyblish.api.InstancePlugin):
    """
        Validate all the nodes underneath skeleton_Anim_SET
        should be reference nodes
    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["animation.fbx"]
    label = "Animated Reference Rig"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    def process(self, instance):
        animated_sets = instance.data["animated_skeleton"]
        for animated_reference in animated_sets:
            is_referenced = cmds.referenceQuery(
                animated_reference, isNodeReferenced=True)
            if not bool(is_referenced):
                raise PublishValidationError(
                    "All the content in skeleton_Anim_SET"
                    " should be reference nodes"
                )
