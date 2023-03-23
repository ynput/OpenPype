import pyblish.api
from openpype.lib import version_up
from pymxs import runtime as rt


class IncrementWorkfileVersion(pyblish.api.ContextPlugin):
    """Increment current workfile version."""

    order = pyblish.api.IntegratorOrder + 0.9
    label = "Increment Workfile Version"
    hosts = ["max"]
    families = ["workfile"]

    def process(self, context):
        path = context.data["currentFile"]
        filepath = version_up(path)

        rt.saveMaxFile(filepath)
        self.log.info("Incrementing file version")
