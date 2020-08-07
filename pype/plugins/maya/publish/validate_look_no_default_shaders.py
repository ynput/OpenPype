from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateLookNoDefaultShaders(pyblish.api.InstancePlugin):
    """Validate if any node has a connection to a default shader.

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

    order = pype.api.ValidateContentsOrder + 0.01
    families = ['look']
    hosts = ['maya']
    label = 'Look No Default Shaders'
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    DEFAULT_SHADERS = {"lambert1", "initialShadingGroup",
                      "initialParticleSE", "particleCloud1"}

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid node relationships found: "
                               "{0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):

        invalid = set()
        for node in instance:
            # Get shading engine connections
            shaders = cmds.listConnections(node, type="shadingEngine") or []

            # Check for any disallowed connections on *all* nodes
            if any(s in cls.DEFAULT_SHADERS for s in shaders):

                # Explicitly log each individual "wrong" connection.
                for s in shaders:
                    if s in cls.DEFAULT_SHADERS:
                        cls.log.error("Node has unallowed connection to "
                                      "'{}': {}".format(s, node))

                invalid.add(node)

        return list(invalid)
