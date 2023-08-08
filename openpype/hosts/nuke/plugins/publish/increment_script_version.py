
import nuke
import pyblish.api


class IncrementScriptVersion(pyblish.api.ContextPlugin):
    """Increment current script version."""

    order = pyblish.api.IntegratorOrder + 0.9
    label = "Increment Script Version"
    optional = True
    families = ["workfile"]
    hosts = ['nuke']

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Publishing not successful so version is not increased.")

        # NOTE hornet update on use existing frames on farm
        render_target = context.data.get("render_target")
        review = context.data.get("review")
        self.log.info('render_target : {} review : {}'.format(render_target,review))
        if review == False or render_target in ['farm','local'] :
            from openpype.lib import version_up
            path = context.data["currentFile"]
            nuke.scriptSaveAs(version_up(path))
            self.log.info('Incrementing script version')
