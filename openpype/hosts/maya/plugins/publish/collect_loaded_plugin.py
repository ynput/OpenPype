import pyblish.api
import avalon.api
from maya import cmds


class CollectLoadedPlugin(pyblish.api.ContextPlugin):
    """Collect loaded plugins"""

    order = pyblish.api.CollectorOrder
    label = "Loaded Plugins"
    hosts = ["maya"]

    def process(self, context):

        context.data["loadedPlugins"] = cmds.pluginInfo(query=True, listPlugins=True)
