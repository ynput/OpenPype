import pyblish.api
from maya import cmds

from openpype.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder
)


class ValidateRigContents(pyblish.api.InstancePlugin):
    """Ensure rig contains pipeline-critical content

    Every rig must contain at least two object sets:
        "controls_SET" - Set of all animatable controls
        "out_SET" - Set of all cacheable meshes

    """

    order = ValidateContentsOrder
    label = "Rig Contents"
    hosts = ["maya"]
    families = ["rig"]

    accepted_output = ["mesh", "transform"]
    accepted_controllers = ["transform"]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Invalid rig content. See log for details.")

    @classmethod
    def get_invalid(cls, instance):

        # Find required sets by suffix
        required, rig_sets = cls.get_nodes(instance)
        missing = [
            key for key in required if key not in rig_sets
        ]
        if missing:
            raise PublishValidationError(
                "%s is missing sets: %s" % (instance, ", ".join(missing))
            )

        controls_set = rig_sets["controls_SET"]
        out_set = rig_sets["out_SET"]

        # Ensure there are at least some transforms or dag nodes
        # in the rig instance
        set_members = instance.data['setMembers']
        if not cmds.ls(set_members, type="dagNode", long=True):
            raise PublishValidationError(
                "No dag nodes in the pointcache instance. "
                "(Empty instance?)"
            )

        # Ensure contents in sets and retrieve long path for all objects
        output_content = cmds.sets(out_set, query=True) or []
        if not output_content:
            raise PublishValidationError("Must have members in rig out_SET")
        output_content = cmds.ls(output_content, long=True)

        controls_content = cmds.sets(controls_set, query=True) or []
        if not controls_content:
            raise PublishValidationError(
                "Must have members in rig controls_SET"
            )
        controls_content = cmds.ls(controls_content, long=True)

        # Validate members are inside the hierarchy from root node
        root_nodes = cmds.ls(set_members, assemblies=True, long=True)
        hierarchy = cmds.listRelatives(root_nodes, allDescendents=True,
                                       fullPath=True) + root_nodes
        hierarchy = set(hierarchy)

        invalid_hierarchy = []
        for node in output_content:
            if node not in hierarchy:
                invalid_hierarchy.append(node)
        for node in controls_content:
            if node not in hierarchy:
                invalid_hierarchy.append(node)

        # Additional validations
        invalid_geometry = cls.validate_geometry(output_content)
        invalid_controls = cls.validate_controls(controls_content)

        error = False
        if invalid_hierarchy:
            cls.log.error("Found nodes which reside outside of root group "
                           "while they are set up for publishing."
                           "\n%s" % invalid_hierarchy)
            error = True

        if invalid_controls:
            cls.log.error("Only transforms can be part of the controls_SET."
                           "\n%s" % invalid_controls)
            error = True

        if invalid_geometry:
            cls.log.error("Only meshes can be part of the out_SET\n%s"
                           % invalid_geometry)
            error = True
        return error

    @classmethod
    def validate_geometry(cls, set_members):
        """Check if the out set passes the validations

        Checks if all its set members are within the hierarchy of the root
        Checks if the node types of the set members valid

        Args:
            set_members: list of nodes of the controls_set
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
            if cmds.nodeType(shape) not in cls.accepted_output:
                invalid.append(shape)

        return invalid

    @classmethod
    def validate_controls(cls, set_members):
        """Check if the controller set passes the validations

        Checks if all its set members are within the hierarchy of the root
        Checks if the node types of the set members valid

        Args:
            set_members: list of nodes of the controls_set
            hierarchy: list of nodes which reside under the root node

        Returns:
            errors (list)
        """

        # Validate control types
        invalid = []
        for node in set_members:
            if cmds.nodeType(node) not in cls.accepted_controllers:
                invalid.append(node)

        return invalid

    @classmethod
    def get_nodes(cls, instance):
        objectsets = ["controls_SET", "out_SET"]
        rig_sets_nodes = instance.data.get("rig_sets", [])
        return objectsets, rig_sets_nodes


class ValidateSkeletonRigContents(ValidateRigContents):
    """Ensure skeleton rigs contains pipeline-critical content

    The rigs optionally contain at least two object sets:
        "skeletonMesh_SET" - Set of the skinned meshes
                             with bone hierarchies

    """

    order = ValidateContentsOrder
    label = "Skeleton Rig Contents"
    hosts = ["maya"]
    families = ["rig.fbx"]

    accepted_output = {"mesh", "transform", "locator"}

    @classmethod
    def get_invalid(cls, instance):
        objectsets, skeleton_mesh_nodes = cls.get_nodes(instance)
        missing = [
            key for key in objectsets if key not in instance.data["rig_sets"]
        ]
        if missing:
            cls.log.debug(
                "%s is missing sets: %s" % (instance, ", ".join(missing))
            )
            return

        # Ensure there are at least some transforms or dag nodes
        # in the rig instance
        set_members = instance.data['setMembers']
        if not cmds.ls(set_members, type="dagNode", long=True):
            raise PublishValidationError(
                "No dag nodes in the pointcache instance. "
                "(Empty instance?)"
            )
        # Ensure contents in sets and retrieve long path for all objects
        output_content = instance.data.get("skeleton_mesh", [])
        output_content = cmds.ls(skeleton_mesh_nodes, long=True)

        # Validate members are inside the hierarchy from root node
        root_nodes = cmds.ls(set_members, assemblies=True, long=True)
        hierarchy = cmds.listRelatives(root_nodes, allDescendents=True,
                                       fullPath=True) + root_nodes
        hierarchy = set(hierarchy)
        error = False
        invalid_hierarchy = []
        if output_content:
            for node in output_content:
                if node not in hierarchy:
                    invalid_hierarchy.append(node)
            invalid_geometry = cls.validate_geometry(output_content)
        if invalid_hierarchy:
            cls.log.error("Found nodes which reside outside of root group "
                           "while they are set up for publishing."
                           "\n%s" % invalid_hierarchy)
            error = True
        if invalid_geometry:
            cls.log.error("Found nodes which reside outside of root group "
                           "while they are set up for publishing."
                           "\n%s" % invalid_hierarchy)
            error = True
        return error

    @classmethod
    def get_nodes(cls, instance):
        objectsets = ["skeletonMesh_SET"]
        skeleton_mesh_nodes = instance.data.get("skeleton_mesh", [])
        return objectsets, skeleton_mesh_nodes
