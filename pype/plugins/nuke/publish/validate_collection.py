import os
import pyblish.api
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


class ValidateCollection(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["render.frames", "still.frames", "prerender.frames"]

    label = "Check prerendered frames"
    hosts = ["nuke"]
    actions = [RepairCollectionAction]

    def process(self, instance):
        self.log.debug('instance.data["files"]: {}'.format(instance.data['files']))
        collections, remainder = clique.assemble(*instance.data['files'])
        self.log.info('collections: {}'.format(str(collections)))

        frame_length = instance.data["endFrame"] \
            - instance.data["startFrame"] + 1

        if frame_length is not 1:
            assert len(collections) == 1, self.log.info(
                "There are multiple collections in the folder")
            assert collections[0].is_contiguous(), self.log.info("Some frames appear to be missing")

        assert remainder is not None, self.log.info("There are some extra files in folder")

        basename, ext = os.path.splitext(list(collections[0])[0])
        assert all(ext == os.path.splitext(name)[1]
                   for name in collections[0]), self.log.info(
            "Files had varying suffixes"
        )

        assert not any(os.path.isabs(name)
                       for name in collections[0]), self.log.info("some file name are absolute")

        self.log.info('frame_length: {}'.format(frame_length))
        self.log.info('len(list(instance.data["files"])): {}'.format(
            len(list(instance.data["files"][0]))))

        assert len(list(instance.data["files"][0])) is frame_length, self.log.info(
            "{} missing frames. Use repair to render all frames".format(__name__))
