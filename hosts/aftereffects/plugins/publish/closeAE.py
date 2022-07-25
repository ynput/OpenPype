# -*- coding: utf-8 -*-
"""Close AE after publish. For Webpublishing only."""
import pyblish.api

from openpype.hosts.aftereffects.api import get_stub


class CloseAE(pyblish.api.ContextPlugin):
    """Close AE after publish. For Webpublishing only.
    """

    order = pyblish.api.IntegratorOrder + 14
    label = "Close AE"
    optional = True
    active = True

    hosts = ["aftereffects"]
    targets = ["remotepublish"]

    def process(self, context):
        self.log.info("CloseAE")

        stub = get_stub()
        self.log.info("Shutting down AE")
        stub.save()
        stub.close()
        self.log.info("AE closed")
