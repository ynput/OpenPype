import pyblish.api
from avalon import (
    io,
    api as avalon
)
import pprint


class CollectContextDataFromAport(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "Collect Aport Context"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        rqst_json_data_path = context.data['rqst_json_data_path']
        post_json_data_path = context.data['post_json_data_path']

        self.log.info("Context.data are: {}".format(
            context.data))

        self.log.info("rqst_json_data_path is: {}".format(rqst_json_data_path))

        self.log.info("post_json_data_path is: {}".format(post_json_data_path))

        self.log.info("avalon.session is: {}".format(avalon.session))
