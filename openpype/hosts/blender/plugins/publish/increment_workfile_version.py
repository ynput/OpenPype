import pyblish.api
from openpype.hosts.blender.api.workio import save_file


class IncrementWorkfileVersion(pyblish.api.ContextPlugin):
    """Increment current workfile version."""

    order = pyblish.api.IntegratorOrder + 0.9
    label = "Increment Workfile Version"
    optional = True
    hosts = ["blender"]
    families = ["animation", "model", "rig", "action", "layout"]

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Publishing not successful so version is not increased.")

        from openpype.lib import version_up
        path = context.data["currentFile"]
        filepath = version_up(path)

        save_file(filepath, copy=False)

        self.log.info('Incrementing script version')
