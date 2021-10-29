import pyblish.api
import openpype.api

import os


class ValidateSources(pyblish.api.InstancePlugin):
    """Validates source files.

        Loops through all 'files' in 'stagingDir' if actually exist. They might
        got deleted between starting of SP and now.

    """

    order = openpype.api.ValidateContentsOrder
    label = "Check source files"

    optional = True  # only for unforeseeable cases

    hosts = ["standalonepublisher"]

    def process(self, instance):
        self.log.info("instance {}".format(instance.data))

        for repre in instance.data.get("representations") or []:
            files = []
            if isinstance(repre["files"], str):
                files.append(repre["files"])
            else:
                files = list(repre["files"])

            for file_name in files:
                source_file = os.path.join(repre["stagingDir"],
                                           file_name)

                if not os.path.exists(source_file):
                    raise ValueError("File {} not found".format(source_file))
