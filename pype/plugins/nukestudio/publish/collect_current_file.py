import pyblish.api


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder

    def process(self, context):
        """Todo, inject the current working file"""

        project = context.data('activeProject')
        context.set_data('currentFile', value=project.path())
        self.log.info("currentFile: {}".format(context.data["currentFile"]))
