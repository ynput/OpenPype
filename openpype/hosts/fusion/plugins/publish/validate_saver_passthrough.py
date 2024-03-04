import pyblish.api
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateSaverPassthrough(pyblish.api.ContextPlugin):
    """Validate saver passthrough is similar to Pyblish publish state"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Passthrough"
    families = ["render", "image"]
    hosts = ["fusion"]
    actions = [SelectInvalidAction]

    def process(self, context):

        # Workaround for ContextPlugin always running, even if no instance
        # is present with the family
        instances = pyblish.api.instances_by_plugin(instances=list(context),
                                                    plugin=self)
        if not instances:
            self.log.debug("Ignoring plugin.. (bugfix)")

        invalid_instances = []
        for instance in instances:
            invalid = self.is_invalid(instance)
            if invalid:
                invalid_instances.append(instance)

        if invalid_instances:
            self.log.info("Reset pyblish to collect your current scene state, "
                          "that should fix error.")
            raise PublishValidationError(
                "Invalid instances: {0}".format(invalid_instances),
                title=self.label)

    def is_invalid(self, instance):

        saver = instance.data["tool"]
        attr = saver.GetAttrs()
        active = not attr["TOOLB_PassThrough"]

        if active != instance.data.get("publish", True):
            self.log.info("Saver has different passthrough state than "
                          "Pyblish: {} ({})".format(instance, saver.Name))
            return [saver]

        return []
