from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateLookNoDefaultShaders(pyblish.api.InstancePlugin):
    """Validate look contains no default shaders.

    This checks whether the look has any members of:
    - lambert1
    - initialShadingGroup
    - initialParticleSE
    - particleCloud1

    If any of those is present it will raise an error. A look is not allowed
    to have any of the "default" shaders present in a scene as they can
    introduce problems when referenced (overriding local scene shaders).

    To fix this no shape nodes in the look must have any of default shaders
    applied.

    """

    order = colorbleed.api.ValidateContentsOrder + 0.01
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look No Default Shaders'
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid node relationships found: "
                               "{0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):
        disallowed = ["lambert1", "initialShadingGroup",
                      "initialParticleSE", "particleCloud1"]
        disallowed = set(disallowed)

        # Check if there are any skinClusters present
        # If so ensure nodes which are skinned
        intermediate = []
        skinclusters = cmds.ls(type="skinCluster")
        cls.log.info("Found skinClusters, will skip original shapes")
        if skinclusters:
            intermediate += cmds.ls(intermediateObjects=True,
                                    shapes=True,
                                    long=True)

        invalid = set()
        for node in instance:

            # get connection
            # listConnections returns a list or None
            object_sets = cmds.listConnections(node, type="objectSet") or []

            # Ensure the shape in the instances have at least a single shader
            # connected if it *can* have a shader, like a `surfaceShape` in
            # Maya.
            if (cmds.objectType(node, isAType="surfaceShape") and
                    not cmds.ls(object_sets, type="shadingEngine")):
                if node in intermediate:
                    continue
                cls.log.error("Detected shape without shading engine: "
                              "'{}'".format(node))
                invalid.add(node)

            # Check for any disallowed connections
            if any(s in disallowed for s in object_sets):

                # Explicitly log each individual "wrong" connection.
                for s in object_sets:
                    if s in disallowed:
                        cls.log.error("Node has unallowed connection to "
                                      "'{}': {}".format(s, node))

                invalid.add(node)

        return list(invalid)
