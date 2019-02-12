import pyblish.api

import avalon.api as api
from avalon.vendor import requests
from pype.plugin import contextplugin_should_run
import os

class ValidateDeadlineConnection(pyblish.api.ContextPlugin):
    """Validate Deadline Web Service is running"""

    label = "Validate Deadline Web Service"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["renderlayer"]

    def process(self, context):

        # Workaround bug pyblish-base#250
        if not contextplugin_should_run(self, context):
            return

        try:
            AVALON_DEADLINE = os.environ["AVALON_DEADLINE"]
        except KeyError:
            self.log.error("Deadline REST API url not found.")

        # Check response
        response = requests.get(AVALON_DEADLINE)
        assert response.ok, "Response must be ok"
        assert response.text.startswith("Deadline Web Service "), (
            "Web service did not respond with 'Deadline Web Service'"
        )
