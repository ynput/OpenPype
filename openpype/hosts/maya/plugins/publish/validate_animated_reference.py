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
    accepted_controllers = ["transform", "locator"]

    def process(self, instance):
        animated_sets = instance.data["animated_skeleton"]
        if not animated_sets:
            self.log.debug(
                "No nodes found in skeleton_Anim_SET..Skipping..")
            return

        for animated_reference in animated_sets:
            is_referenced = cmds.referenceQuery(
                animated_reference, isNodeReferenced=True)
            if not bool(is_referenced):
                raise PublishValidationError(
                    "All the content in skeleton_Anim_SET"
                    " should be reference nodes"
                )
        invalid_controls = self.validate_controls(animated_sets)
        if invalid_controls:
            raise PublishValidationError(
                "All the content in skeleton_Anim_SET"
                " should be the transforms"
            )

    def validate_controls(self, set_members):
        """Check if the controller set passes the validations

        Checks if all its set members are within the hierarchy of the root
        Checks if the node types of the set members valid

        Args:
            set_members: list of nodes of the skeleton_anim_set
            hierarchy: list of nodes which reside under the root node

        Returns:
            errors (list)
        """

        # Validate control types
        invalid = []
        for node in set_members:
            if cmds.nodeType(node) not in self.accepted_controllers:
                invalid.append(node)

        return invalid
