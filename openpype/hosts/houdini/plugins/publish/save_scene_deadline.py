import pyblish.api


class SaveCurrentSceneDeadline(pyblish.api.ContextPlugin):
    """Save current scene"""

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["houdini"]
    targets = ["deadline"]

    def process(self, context):
        import hou

        assert (
            context.data["currentFile"] == hou.hipFile.path()
        ), "Collected filename from current scene name."

        if hou.hipFile.hasUnsavedChanges():
            self.log.info("Saving current file..")
            hou.hipFile.save(save_to_recent_files=True)
        else:
            self.log.debug("No unsaved changes, skipping file save..")
