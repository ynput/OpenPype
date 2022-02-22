import pyblish.api
import avalon.api


class SaveCurrentScene(pyblish.api.ContextPlugin):
    """Save current scene"""

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["houdini"]

    def process(self, context):

        # Filename must not have changed since collecting
        host = avalon.api.registered_host()
        current_file = host.current_file()
        assert context.data['currentFile'] == current_file, (
            "Collected filename from current scene name."
        )

        if host.has_unsaved_changes():
            self.log.info("Saving current file..")
            host.save_file(current_file)
        else:
            self.log.debug("No unsaved changes, skipping file save..")
