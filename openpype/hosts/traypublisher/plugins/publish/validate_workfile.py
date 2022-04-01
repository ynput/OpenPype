import os
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateWorkfilePath(pyblish.api.InstancePlugin):
    """Validate existence of workfile instance existence."""

    label = "Validate Workfile"
    order = pyblish.api.ValidatorOrder - 0.49
    families = ["workfile"]
    hosts = ["traypublisher"]

    def process(self, instance):
        filepath = instance.data["sourceFilepath"]
        if not filepath:
            raise PublishValidationError((
                "Filepath of 'workfile' instance \"{}\" is not set"
            ).format(instance.data["name"]))

        if not os.path.exists(filepath):
            raise PublishValidationError((
                "Filepath of 'workfile' instance \"{}\" does not exist: {}"
            ).format(instance.data["name"], filepath))
