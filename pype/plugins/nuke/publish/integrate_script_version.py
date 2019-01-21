
import nuke
import pyblish.api


class IncrementScriptVersion(pyblish.api.ContextPlugin):
    """Increment current script version."""

    order = pyblish.api.IntegratorOrder + 0.9
    label = "Increment Current Script Version"
    optional = True
    hosts = ['nuke']
    families = ["nukescript", "render.local", "render.frames"]

    def process(self, context):
        # return
        #
        from pype.lib import version_up
        path = context.data["currentFile"]
        nuke.scriptSaveAs(version_up(path))
        self.log.info('Incrementing script version')
