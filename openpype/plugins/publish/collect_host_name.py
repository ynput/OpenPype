"""
Requires:
    None
Provides:
    context -> hostName (str)
"""
import os
import pyblish.api


class CollectHostName(pyblish.api.ContextPlugin):
    """Collect avalon host name to context."""

    label = "Collect Host Name"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        host_name = context.data.get("hostName")
        if host_name:
            return

        # Use AVALON_APP to get host name if available
        context.data["hostName"] = os.environ.get("AVALON_APP")
