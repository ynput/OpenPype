import pyblish.api
import avalon.blender.workio


class IncrementWorkfileVersion(pyblish.api.ContextPlugin):
    """Increment current workfile version."""

    order = pyblish.api.IntegratorOrder + 0.9
    label = "Increment Workfile Version"
    optional = True
    hosts = ["blender"]
    families = ["animation", "model", "rig", "action"]

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Publishing not succesfull so version is not increased.")

        from pype.lib import version_up
        path = context.data["currentFile"]
        filepath = version_up(path)

        avalon.blender.workio.save_file(filepath, copy=False)

        self.log.info('Incrementing script version')
