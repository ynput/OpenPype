import os
import pyblish.api
import clique


@pyblish.api.log
class RepairCollectionAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):
        [os.remove(f) for f in context[0].data["files"]]
        context[0][0]["render"].setValue(True)
        self.log.info("Rendering toggled ON")


class ValidateCollection(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder
    # optional = True
    families = ['prerendered.frames']
    label = "Check prerendered frames"
    hosts = ["nuke"]
    actions = [RepairCollectionAction]

    def process(self, instance):

        collections, remainder = clique.assemble(*instance.data['files'])
        self.log.info('collections: {}'.format(collections))

        frame_length = instance.data["lastFrame"] \
            - instance.data["firstFrame"]

        assert len(collections) == 1, self.log.info("There are multiple collections in the folder")

        assert collections[0].is_contiguous(), self.log.info("Some frames appear to be missing")

        assert len(list(instance.data["files"])) is frame_length, self.log.info(
            "{} missing frames. Use repair to render all frames".format(__name__))
