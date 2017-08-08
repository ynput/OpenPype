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
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look No Default Shaders'
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        invalid = []
        disallowed = ["lambert1",
                      "initialShadingGroup",
                      "initialParticleSE",
                      "particleCloud1"]

        setmembers = instance.data["setMembers"]
        members = cmds.listRelatives(setmembers,
                                     allDescendents=True,
                                     type="shape")

        for member in members:

            # get connection
            # listConnections returns a list or None
            shading_engine = cmds.listConnections(member, type="shadingEngine")
            if not shading_engine:
                cls.log.error("Detected shape without shading engine : "
                              "'{}'".format(member))
                invalid.append(member)
                continue

            # retrieve the shading engine out of the list
            shading_engine = shading_engine[0]
            if shading_engine in disallowed:
                cls.log.error("Member connected to a disallows objectSet: "
                              "'{}'".format(member))
            else:
                continue

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        # sets = self.get_invalid_sets(instance)
        sets = self.get_invalid(instance)
        if sets:
            raise RuntimeError("Invalid shaders found: {0}".format(sets))
