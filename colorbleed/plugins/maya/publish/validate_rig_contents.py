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

    def process(self, instance):

        objectsets = ("controls_SET", "out_SET")
        missing = [obj for obj in objectsets if obj not in instance]

        assert not missing, ("%s is missing %s" % (instance, missing))

        # Ensure there are at least some transforms or dag nodes
        # in the rig instance
        set_members = instance.data['setMembers']
        if not cmds.ls(set_members, type="dagNode", long=True):
            raise RuntimeError("No dag nodes in the pointcache instance. "
                               "(Empty instance?)")

        self.log.info("Evaluating contents of object sets..")

        not_meshes = list()
        not_transforms = list()
        invalid_hierachy = list()

        error = False

        # Ensure contents in sets and retrieve long path for all objects
        out_members = cmds.sets("out_SET", query=True) or []
        assert out_members, "Must have members in rig out_SET"
        out_members = cmds.ls(out_members, long=True)

        controls_members = cmds.sets("controls_SET", query=True) or []
        controls_members = cmds.ls(controls_members, long=True)
        assert controls_members, "Must have controls in rig control_SET"

        root_node = cmds.ls(set_members, assemblies=True)
        root_content = cmds.listRelatives(root_node,
                                          allDescendents=True,
                                          fullPath=True)

        # Validate the contents further
        shapes = cmds.listRelatives(out_members,
                                    allDescendents=True,
                                    shapes=True,
                                    fullPath=True) or []

        # The user can add the shape node to the out_set, this will result
        # in none when querying allDescendents
        out_shapes = out_members + shapes

        # geometry
        for shape in out_shapes:
            nodetype = cmds.nodeType(shape)
            if nodetype in self.ignore_nodes:
                continue

            if nodetype not in self.accepted_output:
                not_meshes.append(shape)

            # check if controllers are in the root group
            if shape not in root_content:
                invalid_hierachy.append(shape)

        # curves
        for node in controls_members:
            nodetype = cmds.nodeType(node)
            if nodetype in self.ignore_nodes:
                continue

            if nodetype not in self.accepted_controllers:
                not_transforms.append(node)

            # check if controllers are in the root group
            if node not in root_content:
                invalid_hierachy.append(node)

        if invalid_hierachy:
            self.log.error("Found nodes which reside outside of root group "
                           "while they are set up for publishing."
                           "\n%s" % invalid_hierachy)
            error = True

        if not_transforms:
            self.log.error("Only transforms can be part of the controls_SET."
                           "\n%s" % not_transforms)
            error = True

        if not_meshes:
            self.log.error("Only meshes can be part of the out_SET\n%s"
                           % not_meshes)
            error = True

        if error:
            raise RuntimeError("Invalid rig content. See log for details.")
