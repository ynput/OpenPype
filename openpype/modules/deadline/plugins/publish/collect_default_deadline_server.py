# -*- coding: utf-8 -*-
"""Collect default Deadline server."""
from openpype.modules import ModulesManager
import pyblish.api


class CollectDefaultDeadlineServer(pyblish.api.ContextPlugin):
    """Collect default Deadline Webservice URL."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Default Deadline Webservice"

    def process(self, context):
        manager = ModulesManager()
        deadline_module = manager.modules_by_name["deadline"]
        # get default deadline webservice url from deadline module
        context.data["defaultDeadline"] = deadline_module.deadline_url
