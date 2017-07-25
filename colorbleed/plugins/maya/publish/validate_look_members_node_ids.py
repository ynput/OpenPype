import maya.cmds as cmds

import pyblish.api
import colorbleed.api


class ValidateLookMembersNodeIds(pyblish.api.InstancePlugin):
    """Validate look members have colorbleed id attributes

    Looks up the contents of the look to see if all its members have
    colorbleed id attributes so they can be connected correctly.

    When invalid it's very likely related to the model not having the id
    attributes that it should have. These should have been generated in the
    work files for the model/rig/fur or alike.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look Members Id Attributes'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @staticmethod
    def get_invalid(instance):

        # Get all members from the sets
        members = []
        relations = instance.data["lookData"]["relationships"]
        for sg in relations:
            sg_members = sg['members']
            sg_members = [member['name'] for member in sg_members]
            members.extend(sg_members)

        # Get all sets

        members = list(set(members))

        # Ensure all nodes have a cbId
        invalid = list()
        for node in members:
            if not cmds.getAttr("{}.cbId".format(node)):
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Members found without "
                               "asset IDs: {0}".format(invalid))
