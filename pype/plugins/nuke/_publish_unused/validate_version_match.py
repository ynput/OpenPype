import os
import pyblish.api
import pype.utils



@pyblish.api.log
class RepairNukeWriteNodeVersionAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):
        import pype.nuke.lib as nukelib
        instances = pype.utils.filter_instances(context, plugin)

        for instance in instances:
            node = instance[0]
            render_path = nukelib.get_render_path(node)
            self.log.info("render_path: {}".format(render_path))
            node['file'].setValue(render_path.replace("\\", "/"))


class ValidateVersionMatch(pyblish.api.InstancePlugin):
    """Checks if write version matches workfile version"""

    label = "Validate Version Match"
    order = pyblish.api.ValidatorOrder
    actions = [RepairNukeWriteNodeVersionAction]
    hosts = ["nuke"]
    families = ['write']

    def process(self, instance):

        assert instance.data['version'] == instance.context.data['version'], "\
            Version in write doesn't match version of the workfile"
