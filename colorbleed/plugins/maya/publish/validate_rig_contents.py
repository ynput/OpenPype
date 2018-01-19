from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateRigContents(pyblish.api.InstancePlugin):
    """Ensure rig contains pipeline-critical content

    Every rig must contain at least two object sets:
        "controls_SET" - Set of all animatable controls
        "out_SET" - Set of all cachable meshes

    """

    order = colorbleed.api.ValidateContentsOrder
    label = "Rig Contents"
    hosts = ["maya"]
    families = ["colorbleed.rig"]

    accepted_output = ["mesh", "transform"]
    accepted_controllers = ["transform"]
    ignore_nodes = []

    invalid_hierarchy = []
    invalid_controls = []
    invalid_geometry = []

    def process(self, instance):

        error = False

        objectsets = ("controls_SET", "out_SET")
        missing = [obj for obj in objectsets if obj not in instance]
        assert not missing, ("%s is missing %s" % (instance, missing))

        # Ensure there are at least some transforms or dag nodes
        # in the rig instance
        set_members = self.check_set_members(instance)

        # Ensure contents in sets and retrieve long path for all objects
        output_content = cmds.sets("out_SET", query=True) or []
        assert output_content, "Must have members in rig out_SET"

        controls_content = cmds.sets("controls_SET", query=True) or []
        assert controls_content, "Must have members in rig controls_SET"

        root_node = cmds.ls(set_members, assemblies=True)
        hierarchy = cmds.listRelatives(root_node, allDescendents=True,
                                       fullPath=True)

        self.invalid_geometry = self.validate_geometry(output_content,
                                                       hierarchy)
        self.invalid_controls = self.validate_controls(controls_content,
                                                       hierarchy)

        if self.invalid_hierarchy:
            self.log.error("Found nodes which reside outside of root group "
                           "while they are set up for publishing."
                           "\n%s" % self.invalid_hierarchy)
            error = True

        if self.invalid_controls:
            self.log.error("Only transforms can be part of the controls_SET."
                           "\n%s" % self.invalid_controls)
            error = True

        if self.invalid_geometry:
            self.log.error("Only meshes can be part of the out_SET\n%s"
                           % self.invalid_geometry)
            error = True

        if error:
            raise RuntimeError("Invalid rig content. See log for details.")

    def check_set_members(self, instance):
        """Check if the instance has any dagNodes
        Args:
            instance: the instance which needs to be published
        Returns:
            set_members (list): all dagNodes from instance
        """

        set_members = instance.data['setMembers']
        if not cmds.ls(set_members, type="dagNode", long=True):
            raise RuntimeError("No dag nodes in the pointcache instance. "
                               "(Empty instance?)")
        return set_members

    def validate_hierarchy(self, hierarchy, nodes):
        """Collect all nodes which are NOT within the hierarchy
        Args:
            hierarchy (list): nodes within the root node
            nodes (list): nodes to check

        Returns:
            errors (list): list of nodes
        """
        errors = []
        for node in nodes:
            if node not in hierarchy:
                errors.append(node)
        return errors

    def validate_geometry(self, set_members, hierarchy):
        """Check if the out set passes the validations

        Checks if all its set members are within the hierarchy of the root
        Checks if the node types of the set members valid

        Args:
            set_members: list of nodes of the controls_set
            hierarchy: list of nodes which reside under the root node

        Returns:
            errors (list)
        """

        errors = []
        # Validate the contents further
        shapes = cmds.listRelatives(set_members,
                                    allDescendents=True,
                                    shapes=True,
                                    fullPath=True) or []

        # The user can add the shape node to the out_set, this will result
        # in none when querying allDescendents
        all_shapes = set_members + shapes
        all_long_names = [cmds.ls(i, long=True)[0] for i in all_shapes]

        # geometry
        invalid_shapes = self.validate_hierarchy(hierarchy,
                                                 all_long_names)
        self.invalid_hierarchy.extend(invalid_shapes)
        for shape in all_shapes:
            nodetype = cmds.nodeType(shape)
            if nodetype in self.ignore_nodes:
                continue

            if nodetype not in self.accepted_output:
                errors.append(shape)

        return errors

    def validate_controls(self, set_members, hierarchy):
        """Check if the controller set passes the validations

        Checks if all its set members are within the hierarchy of the root
        Checks if the node types of the set members valid

        Args:
            set_members: list of nodes of the controls_set
            hierarchy: list of nodes which reside under the root node

        Returns:
            errors (list)
        """

        errors = []
        all_long_names = [cmds.ls(i, long=True)[0] for i in set_members]
        invalid_controllers = self.validate_hierarchy(hierarchy,
                                                      all_long_names)
        self.invalid_hierarchy.extend(invalid_controllers)
        for node in set_members:
            nodetype = cmds.nodeType(node)
            if nodetype in self.ignore_nodes:
                continue

            if nodetype not in self.accepted_controllers:
                errors.append(node)

        return errors
