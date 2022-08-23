import pyblish.api

import openpype.api
from openpype.pipeline import PublishXmlValidationError

class ValidateShotDuplicates(pyblish.api.ContextPlugin):
    """Validating no duplicate names are in context."""

    label = "Validate Shot Duplicates"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder

    def process(self, context):
        shot_names = []
        duplicate_names = []
        for instance in context:
            name = instance.data["name"]
            if name in shot_names:
                duplicate_names.append(name)
            else:
                shot_names.append(name)

        msg = "There are duplicate shot names:\n{}".format(duplicate_names)

        formatting_data = {"duplicates_str": ','.join(duplicate_names)}
        if duplicate_names:
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
