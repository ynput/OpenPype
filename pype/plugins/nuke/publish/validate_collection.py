import os
import pyblish.api
import nuke


@pyblish.api.log
class RepairCollectionAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):
        context[0][0]["render"].setValue(True)
        self.log.info("Rendering toggled ON")


class ValidateCollection(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["write"]
    label = "Check Full Img Sequence"
    hosts = ["nuke"]
    actions = [RepairCollectionAction]

    def process(self, instance):
        if not instance.data["collection"]:
            return

        missing_files = []
        for f in instance.data["collection"]:
            # print f
            if not os.path.exists(f):
                missing_files.append(f)

        for f in missing_files:
            instance.data["collection"].remove(f)

        frame_length = instance.data["last_frame"] - instance.data["first_frame"]

        assert len(list(instance.data["collection"])) is frame_length, self.log.info(
            "{} missing frames. Use repair to render all frames".format(__name__))
