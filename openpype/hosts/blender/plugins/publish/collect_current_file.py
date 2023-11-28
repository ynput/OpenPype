import pyblish.api
from openpype.hosts.blender.api import workio


class CollectBlenderCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Blender Current File"
    hosts = ["blender"]

    def process(self, context):
        """Inject the current working file"""
        current_file = workio.current_file()
        context.data["currentFile"] = current_file
