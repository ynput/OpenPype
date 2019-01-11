import os
import pyblish.api
from avalon import (
    io,
    api as avalon
)


class CollectContextDataFromAport(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "Collect Aport Context"
    order = pyblish.api.CollectorOrder - 0.01

    def process(self, context):
        context.data["avalonSession"] = session = avalon.session
        rqst_json_data_path = context.data['rqst_json_data_path']
        post_json_data_path = context.data['post_json_data_path']
        context.data["stagingDir"] = staging_dir = os.path.dirname(post_json_data_path)

        pyblish.api.deregister_all_hosts()
        pyblish.api.register_host(session["AVALON_APP"])

        context.data["currentFile"] = session["AVALON_WORKDIR"]

        if not os.path.exists(staging_dir):
            os.makedirs(staging_dir)

        self.log.info("Context.data are: {}".format(
            context.data))

        self.log.info("rqst_json_data_path is: {}".format(rqst_json_data_path))

        self.log.info("post_json_data_path is: {}".format(post_json_data_path))

        self.log.info("avalon.session is: {}".format(avalon.session))
