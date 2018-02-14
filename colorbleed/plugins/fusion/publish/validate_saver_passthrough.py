import pyblish.api


class ValidateSaverPassthrough(pyblish.api.InstancePlugin):
    """Validate saver passthrough is similar to Pyblish publish state"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Active"
    families = ["fusion.deadline", "fusion.local"]
    hosts = ["fusion"]

    @classmethod
    def get_invalid(cls, instance):

        saver = instance[0]
        attr = saver.GetAttrs()
        active = not attr["TOOLB_PassThrough"]

        if active != instance.data["publish"]:
            return [saver]

        return []

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Saver has different passthrough state than "
                               "Pyblish: {} ({})".format(instance,
                                                         invalid[0].Name))
