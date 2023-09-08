import pyblish.api
from maya import cmds

from openpype.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder
)


class ValidateSkeletonRigContents(pyblish.api.InstancePlugin):
    """Ensure skeleton rigs contains pipeline-critical content

    The rigs optionally contain at least two object sets:
        "skeletonAnim_SET" - Set of only bone hierarchies
        "skeletonMesh_SET" - Set of all cacheable meshes

    """

    order = ValidateContentsOrder
    label = "Skeleton Rig Contents"
    hosts = ["maya"]
    families = ["rig.fbx"]

    accepted_output = ["mesh", "transform"]
    accepted_controllers = ["transform"]

    def process(self, instance):

        objectsets = ["skeletonAnim_SET", "skeletonMesh_SET"]
        missing = [
            key for key in objectsets if key not in instance.data["rig_sets"]
        ]
        if missing:
            self.log.debug(
                "%s is missing sets: %s" % (instance, ", ".join(missing))
            )
            return

        controls_set = instance.data["rig_sets"]["skeletonAnim_SET"]
        out_set = instance.data["rig_sets"]["skeletonMesh_SET"]
        # Ensure there are at least some transforms or dag nodes
        # in the rig instance
        set_members = instance.data['setMembers']
        if not cmds.ls(set_members, type="dagNode", long=True):
            self.log.debug("Skipping empty instance...")
            return
        # Ensure contents in sets and retrieve long path for all objects
        output_content = cmds.sets(
            out_set, query=True) or []
        output_content = cmds.ls(output_content, long=True)

        controls_content = cmds.sets(
            controls_set, query=True) or []
        controls_content = cmds.ls(controls_content, long=True)

        # Validate members are inside the hierarchy from root node
        root_node = cmds.ls(set_members, assemblies=True)
        hierarchy = cmds.listRelatives(root_node, allDescendents=True,
                                       fullPath=True)
        hierarchy = set(hierarchy)

        invalid_hierarchy = []
        if output_content:
            for node in output_content:
                if node not in hierarchy:
                    invalid_hierarchy.append(node)
            invalid_geometry = self.validate_geometry(output_content)
        if controls_content:
            for node in controls_content:
                if node not in hierarchy:
                    invalid_hierarchy.append(node)
            invalid_controls = self.validate_controls(controls_content)

        error = False
        if invalid_hierarchy:
            self.log.error("Found nodes which reside outside of root group "
                           "while they are set up for publishing."
                           "\n%s" % invalid_hierarchy)
            error = True

        if invalid_controls:
            self.log.error("Only transforms can be part of the "
                           "skeletonAnim_SET. \n%s" % invalid_controls)
            error = True

        if invalid_geometry:
            self.log.error("Only meshes can be part of the "
                           "skeletonMesh_SET\n%s" % invalid_geometry)
            error = True

        if error:
            raise PublishValidationError(
                "Invalid rig content. See log for details.")

    def validate_geometry(self, set_members):
        """Check if the out set passes the validations

        Checks if all its set members are within the hierarchy of the root
        Checks if the node types of the set members valid

        Args:
            set_members: list of nodes of the controls_SET
            hierarchy: list of nodes which reside under the root node

        Returns:
            errors (list)
        """

        # Validate all shape types
        invalid = []
        shapes = cmds.listRelatives(set_members,
                                    allDescendents=True,
                                    shapes=True,
                                    fullPath=True) or []
        all_shapes = cmds.ls(set_members + shapes, long=True, shapes=True)
        for shape in all_shapes:
            if cmds.nodeType(shape) not in self.accepted_output:
                invalid.append(shape)

        return invalid

    def validate_controls(self, set_members):
        """Check if the controller set passes the validations

        Checks if all its set members are within the hierarchy of the root
        Checks if the node types of the set members valid

        Args:
            set_members: list of nodes of the controls_SET
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
