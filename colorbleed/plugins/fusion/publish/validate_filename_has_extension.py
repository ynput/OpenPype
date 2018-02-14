import os

import pyblish.api


class ValidateFilenameHasExtension(pyblish.api.InstancePlugin):
    """Ensure the Saver has an extension in the filename path

    This is to counter any possible file being written as `filename` instead
    of `filename.frame.ext`.
    Fusion does not set an extension for your filename
    when changing the file format of the saver.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Filename Has Extension"
    families = ["fusion.deadline", "colorbleed.imagesequence"]
    hosts = ["fusion"]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found Saver(s) without a extesions")

    @classmethod
    def get_invalid(cls, instance):

        path = instance.data["path"]
        fname, ext = os.path.splitext(path)

        if not ext:
            cls.log.error("%s has no extension specified" %
                          instance[0].Name)
            # Return the tool
            return [instance[0]]

        return []
