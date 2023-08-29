import pyblish.api

from openpype_modules.deadline.abstract_submit_deadline import requests_get


class ValidateDeadlineConnection(pyblish.api.InstancePlugin):
    """Validate Deadline Web Service is running"""

    label = "Validate Deadline Web Service"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya", "nuke"]
    families = ["renderlayer", "render"]

    def process(self, instance):
        # get default deadline webservice url from deadline module
        deadline_url = instance.context.data["defaultDeadline"]
        # if custom one is set in instance, use that
        if instance.data.get("deadlineUrl"):
            deadline_url = instance.data.get("deadlineUrl")
            self.log.debug(
                "We have deadline URL on instance {}".format(deadline_url)
            )
        assert deadline_url, "Requires Deadline Webservice URL"

        # Check response
        response = requests_get(deadline_url)
        assert response.ok, "Response must be ok"
        assert response.text.startswith("Deadline Web Service "), (
            "Web service did not respond with 'Deadline Web Service'"
        )
