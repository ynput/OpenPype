import pyblish.api
import colorbleed.api


class ValidateLookMembers(pyblish.api.InstancePlugin):
    """Validate look members have colorbleed id attributes

    Looks up all relationship members and check if all the members have the
    cbId (colorbleed id) and return all the nodes who fail the test.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Members (ID)'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all meshes"""

        invalid_ids = self.get_invalid(instance)
        if invalid_ids:
            raise RuntimeError("Found invalid nodes.\nNo ID : "
                               "{}".format(invalid_ids))

    @classmethod
    def get_invalid(cls, instance):

        relationships = instance.data["lookData"]["relationships"]
        members = []
        for relationship in relationships.values():
            members.extend(relationship["members"])

        # get the name of the node when there is no UUID
        invalid = [m["name"] for m in members if not m["uuid"]]

        return invalid
