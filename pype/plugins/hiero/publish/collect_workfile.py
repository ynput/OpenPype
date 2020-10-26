import pyblish.api
from pype.hosts import hiero as phiero


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    label = "Collect Workfile and Active Project"
    order = pyblish.api.CollectorOrder - 0.49

    def process(self, context):
        project = phiero.get_current_project()

        context.data["activeProject"] = project
        context.data["currentFile"] = project.path()
        self.log.info("currentFile: {}".format(context.data["currentFile"]))
