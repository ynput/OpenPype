import os
import pyblish.api
import pype.utils


@pyblish.api.log
class RepairNukeWriteNodeAction(pyblish.api.Action):
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


class ValidateNukeWriteNode(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["write.render"]
    label = "Write Node"
    actions = [RepairNukeWriteNodeAction]
    hosts = ["nuke"]

    def process(self, instance):

        # Validate output directory exists, if not creating directories.
        # The existence of the knob is queried because previous version
        # of Nuke did not have this feature.
        if "create_directories" in instance[0].knobs():
            msg = "Use Create Directories"
            assert instance[0].knobs()['create_directories'].value() is True, msg
        else:
            path, file = os.path.split(instance.data['outputFilename'])
            msg = "Output directory doesn't exist: \"{0}\"".format(path)
            assert os.path.exists(path), msg

        # Validate metadata knob
        if "metadata" in instance[0].knobs().keys():
            msg = "Metadata needs to be set to \"all metadata\"."
            assert instance[0]["metadata"].value() == "all metadata", msg
