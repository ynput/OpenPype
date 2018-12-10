
import nuke
import pyblish.api


class IncrementScriptVersion(pyblish.api.InstancePlugin):
    """Increment current script version."""

    order = pyblish.api.IntegratorOrder + 9
    label = "Increment Current Script Version"
    optional = True
    hosts = ['nuke']
    families = ["render.frames"]

    def process(self, instance):
        from pype.lib import version_up
        context = instance.context
        path = context.data["currentFile"]
        nuke.scriptSaveAs(version_up(path))
        self.log.info('Incrementing script version')
