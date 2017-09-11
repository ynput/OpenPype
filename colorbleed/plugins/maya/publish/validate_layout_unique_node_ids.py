import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateLayoutUniqueNodeIds(pyblish.api.InstancePlugin):
    """Validate nodes have unique colorbleed id attributes"""

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.layout']
    hosts = ['maya']
    label = 'Layout Transform Unique Ids'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @staticmethod
    def get_invalid_dict(instance):
        """Return a dictionary mapping of id key to list of member nodes"""
        from maya import cmds

        nodes = cmds.ls(instance, type='transform', long=True)
        referenced = cmds.ls(nodes, referencedNodes=True, long=True)
        non_referenced = set(nodes) - set(referenced)
        members = non_referenced

        # Collect each id with their members
        from collections import defaultdict
        ids = defaultdict(list)
        for member in members:
            id = lib.get_id(member)
            ids[id].append(member)

        # Skip those without IDs (if everything should have an ID that should
        # be another validation)
        ids.pop(None, None)

        # Take only the ids with more than one member
        invalid = dict((id, members) for id, members in ids.iteritems() if
                       len(members) > 1)
        return invalid

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""

        invalid_dict = cls.get_invalid_dict(instance)

        # Take only the ids with more than one member
        invalid = list()
        for members in invalid_dict.itervalues():
            invalid.extend(members)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid_dict(instance)

        if invalid:
            raise RuntimeError("Transforms found with non-unique "
                               "asset IDs: {0}".format(invalid))
