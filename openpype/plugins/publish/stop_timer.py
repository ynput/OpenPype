import os
import requests

import pyblish.api


class StopTimer(pyblish.api.ContextPlugin):
    label = "Stop Timer"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["*"]

    def process(self, context):
        modules_settings = context.data["system_settings"]["modules"]
        if modules_settings["timers_manager"]["disregard_publishing"]:
            webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")
            rest_api_url = "{}/timers_manager/stop_timer".format(webserver_url)
            requests.post(rest_api_url)
