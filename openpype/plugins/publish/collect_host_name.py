"""
Requires:
    None
Provides:
    context -> host (str)
"""
import os
import pyblish.api


class CollectHostName(pyblish.api.ContextPlugin):
    """Collect avalon host name to context."""

    label = "Collect Host Name"
    order = pyblish.api.CollectorOrder

    def process(self, context):
        # Don't override value if is already set
        host_name = context.data.get("host")
        if not host_name:
            context.data["host"] = os.environ.get("AVALON_APP")
