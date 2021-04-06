import pyblish.api

from avalon.vendor import requests
from openpype.plugin import contextplugin_should_run
import os


class ValidateDeadlineConnection(pyblish.api.ContextPlugin):
    """Validate Deadline Web Service is running"""

    label = "Validate Deadline Web Service"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya", "nuke"]
    families = ["renderlayer"]

    def process(self, context):

        # Workaround bug pyblish-base#250
        if not contextplugin_should_run(self, context):
            return

        deadline_url = (
            context.data["system_settings"]
            ["modules"]
            ["deadline"]
            ["DEADLINE_REST_URL"]
        )

        # Check response
        response = self._requests_get(deadline_url)
        assert response.ok, "Response must be ok"
        assert response.text.startswith("Deadline Web Service "), (
            "Web service did not respond with 'Deadline Web Service'"
        )

    def _requests_get(self, *args, **kwargs):
        """ Wrapper for requests, disabling SSL certificate validation if
            DONT_VERIFY_SSL environment variable is found. This is useful when
            Deadline or Muster server are running with self-signed certificates
            and their certificate is not added to trusted certificates on
            client machines.

            WARNING: disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.
        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("OPENPYPE_DONT_VERIFY_SSL", True) else True  # noqa
        return requests.get(*args, **kwargs)
