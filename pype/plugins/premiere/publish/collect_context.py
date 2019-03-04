import pyblish.api


class CollectContextDataPremiera(pyblish.api.ContextPlugin):
    """Collecting data from temp json sent from premiera context"""

    label = "Collect Premiera Context"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        data_path = context.data['rqst_json_data_path']
        self.log.info("Context is: {}".format(data_path))
