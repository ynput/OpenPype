import pyblish.api

from pype.api import get_deadline_url
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

        url = context.data.get("deadlienRestUrl")
        assert url, "Deadline Rest Url is missing"

        # test url. Asserts are part of the function
        get_deadline_url(url)
