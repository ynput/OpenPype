import pyblish.api

from openpype.pipeline import registered_host


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Collect current workfile"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect Current Workfile"
    hosts = ["mrv2"]

    def process(self, context):
        host = registered_host()
        path = host.get_current_workfile()
        context.data['currentFile'] = path
        self.log.debug(f"Collected current workfile: {path}")
