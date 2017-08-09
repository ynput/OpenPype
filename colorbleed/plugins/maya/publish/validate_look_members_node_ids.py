import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateLookMembersHaveId(pyblish.api.InstancePlugin):
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
    label = 'Look Members Have ID Attribute'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Members found without "
                               "asset IDs: {0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):

        # Get all members from the sets
        members = set()
        relations = instance.data["lookData"]["relationships"]
        for relation in relations:
            members.update([member['name'] for member in relation['members']])

        # Ensure all nodes have a cbId
        invalid = list()
        for node in members:
            if not lib.get_id(node):
                invalid.append(node)

        return invalid
