import pyblish.api
from openpype.pipeline.workfile.lock_workfile import (
    is_workfile_lock_enabled,
    remove_workfile_lock
)


class SaveCurrentScene(pyblish.api.ContextPlugin):
    """Save current scene

    """

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["maya"]
    families = ["renderlayer", "workfile"]

    def process(self, context):
        import maya.cmds as cmds

        current = cmds.file(query=True, sceneName=True)
        assert context.data['currentFile'] == current

        # If file has no modifications, skip forcing a file save
        if not cmds.file(query=True, modified=True):
            self.log.debug("Skipping file save as there "
                           "are no modifications..")
            return
        project_name = context.data["projectName"]
        project_settings = context.data["project_settings"]
        # remove lockfile before saving
        if is_workfile_lock_enabled("maya", project_name, project_settings):
            remove_workfile_lock(current)
        self.log.info("Saving current file: {}".format(current))
        cmds.file(save=True, force=True)
