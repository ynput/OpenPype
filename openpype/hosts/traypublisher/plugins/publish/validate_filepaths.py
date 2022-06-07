import os
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateWorkfilePath(pyblish.api.InstancePlugin):
    """Validate existence of workfile instance existence."""

    label = "Validate Workfile"
    order = pyblish.api.ValidatorOrder - 0.49

    hosts = ["traypublisher"]

    def process(self, instance):
        if "sourceFilepaths" not in instance.data:
            self.log.info((
                "Can't validate source filepaths existence."
                " Instance does not have collected 'sourceFilepaths'"
            ))
            return

        filepaths = instance.data.get("sourceFilepaths")

        not_found_files = [
            filepath
            for filepath in filepaths
            if not os.path.exists(filepath)
        ]
        if not_found_files:
            joined_paths = "\n".join([
                "- {}".format(filepath)
                for filepath in not_found_files
            ])
            raise PublishValidationError(
                (
                    "Filepath of '{}' instance \"{}\" does not exist:\n{}"
                ).format(
                    instance.data["family"],
                    instance.data["name"],
                    joined_paths
                ),
                "File not found",
                (
                    "## Files were not found\nFiles\n{}"
                    "\n\nCheck if the path is still available."
                ).format(joined_paths)
            )
