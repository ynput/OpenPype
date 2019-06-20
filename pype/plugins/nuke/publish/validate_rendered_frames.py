import os
import pyblish.api
from pype.api import ValidationException
import clique


@pyblish.api.log
class RepairCollectionAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):

        files_remove = [os.path.join(context[0].data["outputDir"], f)
                        for f in context[0].data["files"]]
        for f in files_remove:
            os.remove(f)
            self.log.debug("removing file: {}".format(f))
        context[0][0]["render"].setValue(True)
        self.log.info("Rendering toggled ON")


class ValidateRenderedFrames(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["render.local"]

    label = "Validate rendered frame"
    hosts = ["nuke", "nukestudio"]
    actions = [RepairCollectionAction]

    def process(self, instance):

        for repre in instance.data.get('representations'):

            if not repre.get('files'):
                msg = ("no frames were collected, "
                       "you need to render them")
                self.log.error(msg)
                raise ValidationException(msg)

            collections, remainder = clique.assemble(repre["files"])
            self.log.info('collections: {}'.format(str(collections)))

            collection = collections[0]

            frame_length = instance.data["endFrame"] \
                - instance.data["startFrame"] + 1

            if frame_length != 1:
                if len(collections) != 1:
                    msg = "There are multiple collections in the folder"
                    self.log.error(msg)
                    raise ValidationException(msg)

                if not collection.is_contiguous():
                    msg = "Some frames appear to be missing"
                    self.log.error(msg)
                    raise ValidationException(msg)

                if remainder is not None:
                    msg = "There are some extra files in folder"
                    self.log.error(msg)
                    raise ValidationException(msg)

            self.log.info('frame_length: {}'.format(frame_length))
            self.log.info('len(collection.indexes): {}'.format(
                len(collection.indexes)))

            assert len(
                collection.indexes
            ) is frame_length, ("{} missing frames. Use "
                                "repair to render all frames").format(__name__)

            instance.data['collection'] = collection
