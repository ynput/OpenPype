import os

import pyblish.api
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateFilenameHasExtension(pyblish.api.InstancePlugin):
    """Ensure the Saver has an extension in the filename path

    This disallows files written as `filename` instead of `filename.frame.ext`.
    Fusion does not always set an extension for your filename when
    changing the file format of the saver.

    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Filename Has Extension"
    families = ["render", "image"]
    hosts = ["fusion"]
    actions = [SelectInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Found Saver without an extension",
                                         title=self.label)

    @classmethod
    def get_invalid(cls, instance):

        path = instance.data["expectedFiles"][0]
        fname, ext = os.path.splitext(path)

        if not ext:
            tool = instance.data["tool"]
            cls.log.error("%s has no extension specified" % tool.Name)
            return [tool]

        return []
