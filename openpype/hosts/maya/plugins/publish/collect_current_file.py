
import pyblish.api

from maya import cmds


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file."""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Maya Current File"
    hosts = ['maya']
    families = ["workfile"]

    def process(self, context):
        """Inject the current working file"""
        context.data['currentFile'] = cmds.file(query=True, sceneName=True)
