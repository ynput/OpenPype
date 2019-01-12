import os
import pyblish.api
from avalon import (
    io,
    api as avalon
)
import json


class CollectContextDataFromAport(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "Collect Aport Context"
    order = pyblish.api.CollectorOrder - 0.1

    def process(self, context):
        context.data["avalonSession"] = session = avalon.session
        rqst_json_data_path = context.data['rqst_json_data_path']
        post_json_data_path = context.data['post_json_data_path']

        context.data["stagingDir"] = \
            staging_dir = os.path.dirname(post_json_data_path)

        with open(rqst_json_data_path) as f:
            context.data['json_data'] = json_data = json.load(f)
        assert json_data, "No `data` in json file"

        host = json_data.get("host", None)
        host_version = json_data.get("hostVersion", None)
        assert host, "No `host` data in json file"
        assert host_version, "No `hostVersion` data in json file"
        context.data["host"] = session["AVALON_APP"] = host
        context.data["hostVersion"] = \
            session["AVALON_APP_VERSION"] = host_version

        pyblish.api.deregister_all_hosts()
        pyblish.api.register_host(host)

        current_file = json_data.get("currentFile", None)
        assert current_file, "No `currentFile` data in json file"
        context.data["currentFile"] = current_file

        presets = json_data.get("presets", None)
        assert presets, "No `presets` data in json file"
        context.data["presets"] = presets

        if not os.path.exists(staging_dir):
            os.makedirs(staging_dir)

        self.log.info("Context.data are: {}".format(
            context.data))

        self.log.info("rqst_json_data_path is: {}".format(rqst_json_data_path))

        self.log.info("post_json_data_path is: {}".format(post_json_data_path))

        self.log.info("avalon.session is: {}".format(avalon.session))
