# -*- coding: utf-8 -*-
"""Collect default Deadline server."""
import pyblish.api
import os


class CollectLocalFtrackCreds(pyblish.api.ContextPlugin):
    """Collect default Royal Render path."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect local ftrack credentials"
    targets = ["rr_control"]

    def process(self, context):
        if os.getenv("FTRACK_API_USER") and os.getenv("FTRACK_API_KEY") and \
                os.getenv("FTRACK_SERVER"):
            return
        ftrack_module = context.data["openPypeModules"]["ftrack"]
        if ftrack_module.enabled:
            creds = ftrack_module.get_credentials()
            os.environ["FTRACK_API_USER"] = creds[0]
            os.environ["FTRACK_API_KEY"] = creds[1]
            os.environ["FTRACK_SERVER"] = ftrack_module.ftrack_url
