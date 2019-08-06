import pyblish.api


class CollectActiveProject(pyblish.api.ContextPlugin):
    """Inject the active project into context"""

    label = "Collect Active Project"
    order = pyblish.api.CollectorOrder - 0.2

    def process(self, context):
        import hiero

        context.data["activeProject"] = hiero.ui.activeSequence().project()
        self.log.info("activeProject: {}".format(context.data["activeProject"]))
