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
