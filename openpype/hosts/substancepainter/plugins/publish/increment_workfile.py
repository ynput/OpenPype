import pyblish.api

from openpype.lib import version_up
from openpype.pipeline import registered_host


class IncrementWorkfileVersion(pyblish.api.ContextPlugin):
    """Increment current workfile version."""

    order = pyblish.api.IntegratorOrder + 1
    label = "Increment Workfile Version"
    optional = True
    hosts = ["substancepainter"]

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Publishing not successful so version is not increased.")

        host = registered_host()
        path = context.data["currentFile"]
        self.log.info(f"Incrementing current workfile to: {path}")
        host.save_workfile(version_up(path))
