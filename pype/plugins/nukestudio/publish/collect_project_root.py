import pyblish.api


class CollectActiveProjectRoot(pyblish.api.ContextPlugin):
    """Inject the active project into context"""

    label = "Collect Project Root"
    order = pyblish.api.CollectorOrder - 0.1

    def process(self, context):
        project = context.data["activeProject"]
        context.data["projectroot"] = project.projectRoot()
