# -*- coding: utf-8 -*-
"""Collect default Deadline server."""
import pyblish.api


class CollectDefaultRRPath(pyblish.api.ContextPlugin):
    """Collect default Royal Render path."""

    order = pyblish.api.CollectorOrder
    label = "Default Royal Render Path"

    def process(self, context):
        try:
            rr_module = context.data.get(
                "openPypeModules")["royalrender"]
        except AttributeError:
            msg = "Cannot get OpenPype Royal Render module."
            self.log.error(msg)
            raise AssertionError(msg)

        # get default deadline webservice url from deadline module
        self.log.debug(rr_module.rr_paths)
        context.data["defaultRRPath"] = rr_module.rr_paths["default"]  # noqa: E501
