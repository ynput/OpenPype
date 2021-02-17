import pyblish.api


class ValidateSaverPassthrough(pyblish.api.ContextPlugin):
    """Validate saver passthrough is similar to Pyblish publish state"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Passthrough"
    families = ["render"]
    hosts = ["fusion"]

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
            raise RuntimeError("Invalid instances: "
                               "{0}".format(invalid_instances))

    def is_invalid(self, instance):

        saver = instance[0]
        attr = saver.GetAttrs()
        active = not attr["TOOLB_PassThrough"]

        if active != instance.data["publish"]:
            self.log.info("Saver has different passthrough state than "
                          "Pyblish: {} ({})".format(instance, saver.Name))
            return [saver]

        return []
