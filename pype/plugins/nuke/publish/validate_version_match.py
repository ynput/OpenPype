import os
import pyblish.api
import pype.utils


@pyblish.api.log
class RepairNukeWriteNodeVersionAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):

        instances = pype.utils.filter_instances(context, plugin)

        for instance in instances:
            if "create_directories" in instance[0].knobs():
                instance[0]['create_directories'].setValue(True)
            else:
                path, file = os.path.split(instance[0].data['outputFilename'])
                self.log.info(path)

                if not os.path.exists(path):
                    os.makedirs(path)

            if "metadata" in instance[0].knobs().keys():
                instance[0]["metadata"].setValue("all metadata")


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
