
import nuke
import pyblish.api


class IncrementScriptVersion(pyblish.api.Extractor):
    """Increment current script version."""

    order = pyblish.api.Extractor.order - 0.35
    label = "Increment Current Script Version"
    optional = True
    hosts = ['nuke']

    def process(self, context):
        from pype.lib import version_up
        path = context.data["currentFile"]
        nuke.scriptSaveAs(version_up(path))
        self.log.info('Incrementing script version')
