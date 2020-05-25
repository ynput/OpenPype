from collections import defaultdict

import pyblish.api
import pype.api
import pype.hosts.maya.action
from pype.hosts.maya import lib


class ValidateNodeIdsUnique(pyblish.api.InstancePlugin):
    """Validate the nodes in the instance have a unique Colorbleed Id

    Here we ensure that what has been added to the instance is unique
    """

    order = pype.api.ValidatePipelineOrder
    label = 'Non Duplicate Instance Members (ID)'
    hosts = ['maya']
    families = ["model",
                "look",
                "rig",
                "yetiRig"]

    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.hosts.maya.action.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found with non-unique "
                               "asset IDs: {0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""

        # Check only non intermediate shapes
        # todo: must the instance itself ensure to have no intermediates?
        # todo: how come there are intermediates?
        from maya import cmds
        instance_members = cmds.ls(instance, noIntermediate=True, long=True)

        # Collect each id with their members
        ids = defaultdict(list)
        for member in instance_members:
            object_id = lib.get_id(member)
            if not object_id:
                continue
            ids[object_id].append(member)

        # Take only the ids with more than one member
        invalid = list()
        for _ids, members in ids.iteritems():
            if len(members) > 1:
                cls.log.error("ID found on multiple nodes: '%s'" % members)
                invalid.extend(members)

        return invalid
