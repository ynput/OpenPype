import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateInstanceHasMembers(pyblish.api.InstancePlugin):
    """Validates instance objectSet has *any* members."""

    order = pype.api.ValidateContentsOrder
    hosts = ["maya"]
    label = 'Instance has members'
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        invalid = list()
        if not instance.data["setMembers"]:
            objectset_name = instance.data['name']
            invalid.append(objectset_name)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Empty instances found: {0}".format(invalid))
