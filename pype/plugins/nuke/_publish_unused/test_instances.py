import pyblish.api


class IncrementTestPlugin(pyblish.api.ContextPlugin):
    """Increment current script version."""

    order = pyblish.api.CollectorOrder + 0.5
    label = "Test Plugin"
    hosts = ['nuke']

    def process(self, context):
        instances = context[:]

        prerender_check = list()
        families_check = list()
        for instance in instances:
            if ("prerender" in str(instance)):
                prerender_check.append(instance)
            if instance.data.get("families", None):
                families_check.append(True)

        if len(prerender_check) != len(families_check):
            self.log.info(prerender_check)
            self.log.info(families_check)
