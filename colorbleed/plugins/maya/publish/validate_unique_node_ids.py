from collections import defaultdict

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateNonDuplicateInstanceMembers(pyblish.api.InstancePlugin):
    """Validate the nodes in the instance have a unique Colorbleed Id

    Here we ensure that what has been added to the instance is unique
    """

    order = colorbleed.api.ValidatePipelineOrder
    label = 'Non Duplicate Instance Members (ID)'
    hosts = ['maya']
    families = ["colorbleed.model",
                "colorbleed.look",
                "colorbleed.rig"]

    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid_dict(instance)
        if invalid:
            raise RuntimeError("Nodes found with non-unique "
                               "asset IDs: {0}".format(invalid))


    @classmethod
    def get_invalid_dict(cls, instance):
        """Return a dictionary mapping of id key to list of member nodes"""

        # Collect each id with their members
        ids = defaultdict(list)
        for member in instance:
            object_id = lib.get_id(member)
            if not object_id:
                continue
            ids[object_id].append(member)

        # Skip those without IDs (if everything should have an ID that should
        # be another validation)
        ids.pop(None, None)

        # Take only the ids with more than one member
        invalid = dict((_id, members) for _id, members in ids.iteritems() if
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