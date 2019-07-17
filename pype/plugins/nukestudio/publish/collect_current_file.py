import pyblish.api

class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.1


    def process(self, context):

        project = context.data('activeProject')
        context.data["currentFile"] = path = project.path()
        self.log.info("currentFile: {}".format(context.data["currentFile"]))
