"""
Requires:
    None
Provides:
    context -> host (str)
"""
import os
import pyblish.api

from openpype.lib import ApplicationManager


class CollectHostName(pyblish.api.ContextPlugin):
    """Collect avalon host name to context."""

    label = "Collect Host Name"
    order = pyblish.api.CollectorOrder - 1

    def process(self, context):
        host_name = context.data.get("hostName")
        # Don't override value if is already set
        if host_name:
            return

        # Use AVALON_APP as first if available it is the same as host name
        # - only if is not defined use AVALON_APP_NAME (e.g. on Farm) and
        #   set it back to AVALON_APP env variable
        host_name = os.environ.get("AVALON_APP")
        if not host_name:
            app_name = os.environ.get("AVALON_APP_NAME")
            if app_name:
                app_manager = ApplicationManager()
                app = app_manager.applications.get(app_name)
                if app:
                    host_name = app.host_name

        context.data["hostName"] = host_name
