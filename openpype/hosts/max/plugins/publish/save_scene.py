import pyblish.api
from openpype.pipeline import registered_host


class SaveCurrentScene(pyblish.api.ContextPlugin):
    """Save current scene"""

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["max"]
    families = ["maxrender", "workfile"]

    def process(self, context):
        host = registered_host()
        current_file = host.get_current_workfile()

        assert context.data["currentFile"] == current_file

        if host.workfile_has_unsaved_changes():
            self.log.info(f"Saving current file: {current_file}")
            host.save_workfile(current_file)
        else:
            self.log.debug("No unsaved changes, skipping file save..")
