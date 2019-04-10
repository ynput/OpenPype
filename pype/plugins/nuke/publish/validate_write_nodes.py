import os
import pyblish.api
import pype.utils

@pyblish.api.log
class RepairNukeWriteNodeAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):
        import pype.nuke.lib as nukelib
        instances = pype.utils.filter_instances(context, plugin)

        for instance in instances:
            node = instance[0]
            render_path = nukelib.get_render_path(node).replace("\\", "/")
            self.log.info("render_path: {}".format(render_path))
            node['file'].setValue(render_path)

            if "create_directories" in instance[0].knobs():
                node['create_directories'].setValue(True)
            else:
                path, file = os.path.split(render_path)
                self.log.info(path)

                if not os.path.exists(path):
                    os.makedirs(path)

            if "metadata" in node.knobs().keys():
                instance[0]["metadata"].setValue("all metadata")


class ValidateNukeWriteNode(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["write"]
    label = "Write Node"
    actions = [RepairNukeWriteNodeAction]
    hosts = ["nuke"]

    def process(self, instance):
        import pype.nuke.lib as nukelib
        # validate: create_directories, created path, node file knob, version, metadata
        # TODO: colorspace, dataflow from presets
        node = instance[0]
        render_path = nukelib.get_render_path(node).replace("\\", "/")
        self.log.info("render_path: {}".format(render_path))

        msg_file = "path is not correct"
        assert node['file'].value() is render_path, msg_file

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
