import pyblish.api

from openpype.pipeline import (
    registered_host,
    KnownPublishError
)


class SaveCurrentWorkfile(pyblish.api.ContextPlugin):
    """Save current workfile"""

    label = "Save current workfile"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["substancepainter"]

    def process(self, context):

        host = registered_host()
        current = host.get_current_workfile()
        if context.data["currentFile"] != current:
            raise KnownPublishError("Workfile has changed during publishing!")

        if host.workfile_has_unsaved_changes():
            self.log.info("Saving current file: {}".format(current))
            host.save_workfile()
        else:
            self.log.debug("Skipping workfile save because there are no "
                           "unsaved changes.")
