
import nuke
import pyblish.api


class IncrementScriptVersion(pyblish.api.ContextPlugin):
    """Increment current script version."""

    order = pyblish.api.IntegratorOrder + 0.9
    label = "Increment Script Version"
    optional = True
    families = ["workfile", "render", "render.local", "render.farm"]
    hosts = ['nuke']

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Publishing not succesfull so version is not increased.")

        from pype.lib import version_up
        path = context.data["currentFile"]
        nuke.scriptSaveAs(version_up(path))
        self.log.info('Incrementing script version')
