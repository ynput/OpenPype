import os
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateFilePath(pyblish.api.InstancePlugin):
    """Validate existence of source filepaths on instance.

    Plugins looks into key 'sourceFilepaths' and validate if paths there
    actually exist on disk.

    Also validate if the key is filled but is empty. In that case also
    crashes so do not fill the key if unfilled value should not cause error.

    This is primarily created for Simple Creator instances.
    """

    label = "Validate Workfile"
    order = pyblish.api.ValidatorOrder - 0.49

    hosts = ["traypublisher"]

    def process(self, instance):
        if "sourceFilepaths" not in instance.data:
            self.log.info((
                "Skipped validation of source filepaths existence."
                " Instance does not have collected 'sourceFilepaths'"
            ))
            return

        filepaths = instance.data["sourceFilepaths"]
        if not filepaths:
            raise PublishValidationError(
                (
                    "Source filepaths of '{}' instance \"{}\" are not filled"
                ).format(instance.data["family"], instance.data["name"]),
                "File not filled",
                (
                    "## Files were not filled"
                    "\nThis could mean that you didn't enter files into file"
                    "input."
                )
            )

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
