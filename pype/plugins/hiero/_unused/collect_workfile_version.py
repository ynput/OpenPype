import pyblish.api
import pype.api as pype

class CollectWorkfileVersion(pyblish.api.ContextPlugin):
    """Inject the current working file version into context"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Collect workfile version"

    def process(self, context):

        project = context.data('activeProject')
        path = project.path()
        context.data["version"] = int(pype.get_version_from_path(path))
        self.log.info("version: {}".format(context.data["version"]))
