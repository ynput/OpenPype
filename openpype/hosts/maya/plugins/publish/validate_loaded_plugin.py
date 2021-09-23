import pyblish.api
import maya.cmds as cmds
import openpype.api

class ValidateLoadedPlugin(pyblish.api.ContextPlugin):
    """Ensure there are no unauthorized loaded plugins"""

    label = "Loaded Plugin"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    actions = [openpype.api.RepairContextAction]

    @classmethod
    def get_invalid(cls, context):

        invalid = []

        for plugin in context.data.get("loadedPlugins"):
            if plugin not in cls.authorized_plugins:
                invalid.append(plugin)

        return invalid

    def process(self, context):

        invalid = self.get_invalid(context)
        if invalid:
            raise RuntimeError(
                "Found forbidden plugin name: {}".format(", ".join(invalid))
            )

    @classmethod
    def repair(cls, context):
        """Unload forbidden plugins"""

        for plugin in cls.get_invalid(context):
            cmds.unloadPlugin(plugin, force=True)
