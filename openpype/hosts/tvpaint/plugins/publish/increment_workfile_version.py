import pyblish.api

from openpype.api import version_up
from openpype.hosts.tvpaint.api import workio


class IncrementWorkfileVersion(pyblish.api.ContextPlugin):
    """Increment current workfile version."""

    order = pyblish.api.IntegratorOrder + 1
    label = "Increment Workfile Version"
    optional = True
    hosts = ["tvpaint"]

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Publishing not successful so version is not increased.")

        path = context.data["currentFile"]
        workio.save_file(version_up(path))
        self.log.info('Incrementing workfile version')
