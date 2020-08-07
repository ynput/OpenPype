import os
import pyblish.api
from avalon import (
    io,
    api as avalon
)
import json
from pathlib import Path


class CollectContextDataFromAport(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "AdobeCommunicator Collect Context"
    order = pyblish.api.CollectorOrder - 0.49

    def process(self, context):
        self.log.info(
            "registred_hosts: `{}`".format(pyblish.api.registered_hosts()))
        io.install()
        # get json paths from data
        input_json_path = os.environ.get("AC_PUBLISH_INPATH")
        output_json_path = os.environ.get("AC_PUBLISH_OUTPATH")

        rqst_json_data_path = Path(input_json_path)
        post_json_data_path = Path(output_json_path)

        context.data['post_json_data_path'] = str(post_json_data_path)

        # get avalon session data and convert \ to /
        _S = avalon.session

        asset = _S["AVALON_ASSET"]
        workdir = Path(_S["AVALON_WORKDIR"]).resolve()
        _S["AVALON_WORKDIR"] = str(workdir)

        context.data["avalonSession"] = _S
        self.log.info(f"__ avalonSession: `{_S}`")

        # get stagin directory from recieved path to json
        context.data["stagingDir"] = post_json_data_path.parent

        # get data from json file recieved
        with rqst_json_data_path.open(mode='r') as f:
            context.data["jsonData"] = json_data = json.load(f)
        assert json_data, "No `data` in json file"

        # get and check host type
        host = json_data.get("host", None)
        host_version = json_data.get("hostVersion", None)
        assert host, "No `host` data in json file"
        assert host_version, "No `hostVersion` data in json file"
        context.data["host"] = _S["AVALON_APP"] = host
        context.data["hostVersion"] = \
            _S["AVALON_APP_VERSION"] = host_version

        # get current file
        current_file = json_data.get("currentFile", None)
        assert current_file, "No `currentFile` data in json file"
        context.data["currentFile"] = str(Path(current_file).resolve())

        # get project data from avalon
        project_data = io.find_one({'type': 'project'})
        assert project_data, "No `project_data` data in avalon db"
        context.data["projectData"] = project_data
        self.log.debug("project_data: {}".format(project_data))

        # get asset data from avalon and fix all paths
        asset_data = io.find_one({
            "type": 'asset',
            "name": asset
        })["data"]
        assert asset_data, "No `asset_data` data in avalon db"

        context.data["assetData"] = asset_data

        self.log.debug("asset_data: {}".format(asset_data))
        self.log.info("rqst_json_data_path is: {}".format(rqst_json_data_path))
        self.log.info("post_json_data_path is: {}".format(post_json_data_path))

        # self.log.info("avalon.session is: {}".format(avalon.session))
