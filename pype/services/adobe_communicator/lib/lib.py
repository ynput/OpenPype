import os
import re
import json
import bson
import bson.json_util
from pype.services.rest_api import RestApi, abort, CallbackResult
from .io_nonsingleton import DbConnector
from .publishing import run_publish, set_context

from pypeapp import config, Logger


log = Logger().get_logger("AdobeCommunicator")


class AdobeRestApi(RestApi):
    dbcon = DbConnector()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dbcon.install()

    @RestApi.route("/presets/<project_name>",
                   url_prefix="/adobe",
                   methods="GET")
    def get_presets(self, request):
        project_name = request.url_data["project_name"]
        return CallbackResult(data=config.get_presets(project_name))

    @RestApi.route("/publish", url_prefix="/adobe", methods="POST")
    def publish(self, request):
        """
        http://localhost:8021/adobe/publish
        """
        data = request.request_data

        log.info('Pyblish is running')
        try:
            set_context(
                self.dbcon,
                data
            )
            result = run_publish(data)

            if result:
                return CallbackResult(data=self.result_to_json(result))
        finally:
            log.info('Pyblish have stopped')
    def _prepare_publish_environments(self, data):
        """Prepares environments based on request data."""
        env = copy.deepcopy(os.environ)

        project_name = data["project"]
        asset_name = data["asset"]

        project_doc = self.dbcon[project_name].find_one({
            "type": "project"
        })
        av_asset = self.dbcon[project_name].find_one({
            "type": "asset",
            "name": asset_name
        })
        parents = av_asset["data"]["parents"]
        hierarchy = ""
        if parents:
            hierarchy = "/".join(parents)

        env["AVALON_PROJECT"] = project_name
        env["AVALON_ASSET"] = asset_name
        env["AVALON_TASK"] = data["task"]
        env["AVALON_WORKDIR"] = data["workdir"]
        env["AVALON_HIERARCHY"] = hierarchy
        env["AVALON_PROJECTCODE"] = project_doc["data"].get("code", "")
        env["AVALON_APP"] = data["host"]
        env["AVALON_APP_NAME"] = data["host"]

        env["PYBLISH_HOSTS"] = data["host"]

        env["PUBLISH_PATHS"] = os.pathsep.join(PUBLISH_PATHS)

        # Input and Output paths where source data and result data will be
        # stored
        env["AC_PUBLISH_INPATH"] = data["adobePublishJsonPathSend"]
        env["AC_PUBLISH_OUTPATH"] = data["adobePublishJsonPathGet"]

        return env
