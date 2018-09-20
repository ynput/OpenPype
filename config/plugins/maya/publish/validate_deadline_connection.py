import pyblish.api

import avalon.api as api
from avalon.vendor import requests


class ValidateDeadlineConnection(pyblish.api.ContextPlugin):
    """Validate Deadline Web Service is running"""

    label = "Validate Deadline Web Service"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["studio.renderlayer"]

    def process(self, instance):

        AVALON_DEADLINE = api.Session.get("AVALON_DEADLINE",
                                          "http://localhost:8082")

        assert AVALON_DEADLINE is not None, "Requires AVALON_DEADLINE"

        # Check response
        response = requests.get(AVALON_DEADLINE)
        assert response.ok, "Response must be ok"
        assert response.text.startswith("Deadline Web Service "), \
            "Web service did not respond with 'Deadline Web Service'"