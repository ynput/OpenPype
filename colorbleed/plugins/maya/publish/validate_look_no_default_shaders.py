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

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look No Default Shaders'
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid_sets(cls, instance):

        disallowed = ["lambert1",
                      "initialShadingGroup",
                      "initialParticleSE",
                      "particleCloud1"]
        disallowed = set(disallowed)

        # Check among the sets
        lookdata = instance.data["lookData"]
        sets = lookdata['sets']
        lookup = set(sets)
        intersect = lookup.intersection(disallowed)
        if intersect:
            cls.log.error("Default shaders found in the "
                          "look: {0}".format(list(intersect)))
            return list(intersect)

        # Check among history/inputs of the sets
        history = cmds.listHistory(sets) or []
        lookup = set(history)

        intersect = lookup.intersection(disallowed)
        if intersect:
            cls.log.error("Default shaders found in the history of the "
                          "look: {0}".format(list(intersect)))
            return list(intersect)

        return list()

    @classmethod
    def get_invalid(cls, instance):

        shaders = cls.get_invalid_sets(instance)
        nodes = instance[:]

        # Get members of the shaders
        all = set()
        for shader in shaders:
            members = cmds.sets(shader, query=True) or []
            members = cmds.ls(members, long=True)
            all.update(members)

        # Get the instance nodes among the shader members
        invalid = all.intersection(nodes)
        invalid = list(invalid)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        sets = self.get_invalid_sets(instance)
        if sets:
            raise RuntimeError("Invalid shaders found: {0}".format(sets))
