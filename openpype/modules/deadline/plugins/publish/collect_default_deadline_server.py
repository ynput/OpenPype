# -*- coding: utf-8 -*-
"""Collect default Deadline server."""
import pyblish.api


class CollectDefaultDeadlineServer(pyblish.api.ContextPlugin):
    """Collect default Deadline Webservice URL."""

    order = pyblish.api.CollectorOrder + 0.410
    label = "Default Deadline Webservice"

    pass_mongo_url = False

    def process(self, context):
        try:
            deadline_module = context.data.get("openPypeModules")["deadline"]
        except AttributeError:
            self.log.error("Cannot get OpenPype Deadline module.")
            raise AssertionError("OpenPype Deadline module not found.")

        # get default deadline webservice url from deadline module
        self.log.debug(deadline_module.deadline_urls)
        context.data["defaultDeadline"] = deadline_module.deadline_urls["default"]  # noqa: E501

        context.data["deadlinePassMongoUrl"] = self.pass_mongo_url
