import maya.cmds as cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateLookMembers(pyblish.api.InstancePlugin):
    """Validate look members have colorbleed id attributes

    Looks up the contents of the look to see if all its members have
    Colorbleed Id attributes so they can be connected correctly.

    When invalid it's very likely related to the model not having the id
    attributes that it should have. These should have been generated in the
    work files for the model/rig/fur or alike.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Members'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        invalid_ids = self.get_invalid(instance)
        if invalid_ids:
            raise RuntimeError("Members found without "
                               "asset IDs: {0}".format(invalid_ids))

    @classmethod
    def get_invalid(cls, instance):

        members = set()
        relationships = instance.data["lookData"]["relationships"]
        for relation in relationships:
            members.update([member['name'] for member in relation['members']])

        invalid = [m for m in members if not lib.get_id(m)]
        if invalid:
            raise RuntimeError("Found invalid nodes.\nNo ID : "
                               "{}".format(invalid))

