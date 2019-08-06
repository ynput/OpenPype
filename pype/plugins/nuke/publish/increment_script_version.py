
import nuke
import pyblish.api


class IncrementScriptVersion(pyblish.api.ContextPlugin):
    """Increment current script version."""

    order = pyblish.api.IntegratorOrder + 0.9
    label = "Increment Script Version"
    optional = True
    hosts = ['nuke']

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        instances = context[:]

        prerender_check = list()
        families_check = list()
        for instance in instances:
            if ("prerender" in str(instance)) and instance.data.get("families", None):
                prerender_check.append(instance)
            if instance.data.get("families", None):
                families_check.append(True)


        if len(prerender_check) != len(families_check):
            from pype.lib import version_up
            path = context.data["currentFile"]
            nuke.scriptSaveAs(version_up(path))
            self.log.info('Incrementing script version')
