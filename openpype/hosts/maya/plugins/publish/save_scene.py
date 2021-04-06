import pyblish.api


class SaveCurrentScene(pyblish.api.ContextPlugin):
    """Save current scene

    """

    label = "Save current file"
    order = pyblish.api.IntegratorOrder - 0.49
    hosts = ["maya"]
    families = ["renderlayer"]

    def process(self, context):
        import maya.cmds as cmds

        current = cmds.file(query=True, sceneName=True)
        assert context.data['currentFile'] == current

        self.log.info("Saving current file..")
        cmds.file(save=True, force=True)
