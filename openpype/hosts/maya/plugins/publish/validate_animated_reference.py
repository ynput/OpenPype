import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder,
    OptionalPyblishPluginMixin
)
from maya import cmds


class ValidateAnimatedReferenceRig(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """Validate all nodes in skeletonAnim_SET are referenced"""

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["animation.fbx"]
    label = "Animated Reference Rig"
    accepted_controllers = ["transform", "locator"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        animated_sets = instance.data.get("animated_skeleton", [])
        if not animated_sets:
            self.log.debug(
                "No nodes found in skeletonAnim_SET. "
                "Skipping validation of animated reference rig..."
            )
            return

        for animated_reference in animated_sets:
            is_referenced = cmds.referenceQuery(
                animated_reference, isNodeReferenced=True)
            if not bool(is_referenced):
                raise PublishValidationError(
                    "All the content in skeletonAnim_SET"
                    " should be referenced nodes"
                )
        invalid_controls = self.validate_controls(animated_sets)
        if invalid_controls:
            raise PublishValidationError(
                "All the content in skeletonAnim_SET"
                " should be transforms"
            )

    @classmethod
    def validate_controls(self, set_members):
        """Check if the controller set contains only accepted node types.

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
        set_members = cmds.ls(set_members, long=True)
        for node in set_members:
            if cmds.nodeType(node) not in self.accepted_controllers:
                invalid.append(node)

        return invalid
