import os
import pyblish.api


class CollectCurrentShellFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Current File"
    hosts = ["shell"]

    def process(self, context):
        """Inject the current working file"""
        context.data["currentFile"] = os.path.join(os.getcwd(), "<shell>")
