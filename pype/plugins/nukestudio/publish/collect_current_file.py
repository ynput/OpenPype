import pyblish.api
import pype.api as pype

class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.1


    def process(self, context):
        """Todo, inject the current working file"""

        project = context.data('activeProject')
        context.data["currentFile"] = path = project.path()
        context.data["version"] = pype.get_version_from_path(path)
        self.log.info("currentFile: {}".format(context.data["currentFile"]))
        self.log.info("version: {}".format(context.data["version"]))
