import pyblish.api


class CollectContextDataEditorial(pyblish.api.ContextPlugin):
    """Collecting data from temp json sent from premiera context"""

    label = "Collect Editorial Context"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        data_path = context.data['json_context_data_path']
        self.log.info("Context is: {}".format(data_path))
