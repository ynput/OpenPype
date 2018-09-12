import hou

import pyblish.api


class CollectMayaCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Houdini Current File"
    hosts = ['houdini']

    def process(self, context):
        """Inject the current working file"""
        context.data['currentFile'] = hou.hipFile.path()
