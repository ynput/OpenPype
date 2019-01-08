import pyblish.api
import os

import avalon.api as api
from avalon.vendor import requests


class ValidateDeadlineConnection(pyblish.api.ContextPlugin):
    """Validate Deadline Web Service is running"""

    label = "Validate Deadline Web Service"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["renderlayer"]

    def process(self, instance):

        deadline_url = os.environ.get('DEADLINE_REST_URL', None)
        if deadline_url is None:
            self.log.error("Deadline REST API url not found.")
            raise ValueError("Deadline REST API url not found.")

        # Check response
        response = requests.get(deadline_url)
        assert response.ok, "Response must be ok"
        assert response.text.startswith("Deadline Web Service "), (
            "Web service did not respond with 'Deadline Web Service'"
        )
