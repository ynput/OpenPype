import pyblish.api

from avalon.vendor import requests
from pype.plugin import contextplugin_should_run
import os


class ValidateDeadlineConnection(pyblish.api.ContextPlugin):
    """Validate Deadline Web Service is running"""

    label = "Validate Deadline Web Service"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["renderlayer"]
    if not os.environ.get("DEADLINE_REST_URL"):
        active = False

    def process(self, context):

        # Workaround bug pyblish-base#250
        if not contextplugin_should_run(self, context):
            return

        try:
            DEADLINE_REST_URL = os.environ["DEADLINE_REST_URL"]
        except KeyError:
            self.log.error("Deadline REST API url not found.")
            raise ValueError("Deadline REST API url not found.")

        # Check response
        response = requests.get(DEADLINE_REST_URL)
        assert response.ok, "Response must be ok"
        assert response.text.startswith("Deadline Web Service "), (
            "Web service did not respond with 'Deadline Web Service'"
        )
