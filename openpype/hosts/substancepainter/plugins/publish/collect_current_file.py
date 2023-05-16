import pyblish.api

from openpype.pipeline import registered_host


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Current Workfile"
    hosts = ["substancepainter"]

    def process(self, context):
        host = registered_host()
        path = host.get_current_workfile()
        context.data["currentFile"] = path
        self.log.debug(f"Current workfile: {path}")
