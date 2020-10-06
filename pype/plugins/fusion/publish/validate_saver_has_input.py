import pyblish.api


class ValidateSaverHasInput(pyblish.api.InstancePlugin):
    """Validate saver has incoming connection

    This ensures a Saver has at least an input connection.

    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Has Input"
    families = ["render"]
    hosts = ["fusion"]

    @classmethod
    def get_invalid(cls, instance):

        saver = instance[0]
        if not saver.Input.GetConnectedOutput():
            return [saver]

        return []

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Saver has no incoming connection: "
                               "{} ({})".format(instance, invalid[0].Name))
