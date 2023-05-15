import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateInstanceHasMembers(pyblish.api.InstancePlugin):
    """Validates instance objectSet has *any* members."""

    order = ValidateContentsOrder
    hosts = ["maya"]
    label = 'Instance has members'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()
        if not instance.data["setMembers"]:
            objectset_name = instance.data['name']
            invalid.append(objectset_name)

        return invalid

    def process(self, instance):
        # Allow renderlayer and workfile to be empty
        skip_families = ["workfile", "renderlayer", "rendersetup"]
        if instance.data.get("family") in skip_families:
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Empty instances found: {0}".format(invalid))
