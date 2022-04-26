import pyblish.api
import maya.cmds as cmds
import openpype.api
import os


class ValidateLoadedPlugin(pyblish.api.ContextPlugin):
    """Ensure there are no unauthorized loaded plugins"""

    label = "Loaded Plugin"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    actions = [openpype.api.RepairContextAction]

    @classmethod
    def get_invalid(cls, context):

        invalid = []
        loaded_plugin = cmds.pluginInfo(query=True, listPlugins=True)
        # get variable from OpenPype settings
        whitelist_native_plugins = cls.whitelist_native_plugins
        authorized_plugins = cls.authorized_plugins or []

        for plugin in loaded_plugin:
            if not whitelist_native_plugins and os.getenv('MAYA_LOCATION') \
                    in cmds.pluginInfo(plugin, query=True, path=True):
                continue
            if plugin not in authorized_plugins:
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
            cmds.pluginInfo(plugin, edit=True, autoload=False)
            cmds.unloadPlugin(plugin, force=True)
