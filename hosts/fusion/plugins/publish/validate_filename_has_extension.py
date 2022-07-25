import os

import pyblish.api


class ValidateFilenameHasExtension(pyblish.api.InstancePlugin):
    """Ensure the Saver has an extension in the filename path

    This disallows files written as `filename` instead of `filename.frame.ext`.
    Fusion does not always set an extension for your filename when
    changing the file format of the saver.

    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Filename Has Extension"
    families = ["render"]
    hosts = ["fusion"]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found Saver without an extension")

    @classmethod
    def get_invalid(cls, instance):

        path = instance.data["path"]
        fname, ext = os.path.splitext(path)

        if not ext:
            tool = instance[0]
            cls.log.error("%s has no extension specified" % tool.Name)
            return [tool]

        return []
