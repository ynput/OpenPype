import pyblish.api
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateSaverHasInput(pyblish.api.InstancePlugin):
    """Validate saver has incoming connection

    This ensures a Saver has at least an input connection.

    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Has Input"
    families = ["render", "image"]
    hosts = ["fusion"]
    actions = [SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        saver = instance.data["tool"]
        if not saver.Input.GetConnectedOutput():
            return [saver]

        return []

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            saver_name = invalid[0].Name
            raise PublishValidationError(
                "Saver has no incoming connection: {} ({})".format(instance,
                                                                   saver_name),
                title=self.label)
