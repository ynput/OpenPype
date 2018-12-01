import os
import pyblish.api


@pyblish.api.log
class RepairCollectionAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, instance, plugin):
        self.log.info("this is going to be repaired")


class ValidateCollection(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["write"]
    label = "Check Full Img Sequence"
    hosts = ["nuke"]
    actions = [RepairCollectionAction]

    def process(self, instance):

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
