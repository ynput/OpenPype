"""
Requires:
    openPypeModules (ModulesManager)

Provides:
    context -> hostName (str)
    context -> appName (str)
    context -> appLabel (str)
"""
import os
import pyblish.api


class CollectAppName(pyblish.api.ContextPlugin):
    """Collect app name to context."""

    label = "Collect App Name"
    order = pyblish.api.CollectorOrder - 0.49

    def process(self, context):
        modules_manager = context.data["openPypeModules"]
        host_name = context.data.get("hostName")
        app_name = context.data.get("appName")
        app_label = context.data.get("appLabel")
        # Don't override value if is already set
        if host_name and app_name and app_label:
            return

        # Use AVALON_APP_NAME to get full app name
        if not app_name:
            app_name = os.environ.get("AVALON_APP_NAME")

        # Fill missing values based on app full name
        if (not host_name or not app_label) and app_name:
            apps_addon = modules_manager.get_enabled_modules("applications")
            app_manager = apps_addon.create_applications_manager()
            app = app_manager.applications.get(app_name)
            if app:
                if not host_name:
                    host_name = app.host_name
                if not app_label:
                    app_label = app.full_label

        context.data["hostName"] = host_name
        context.data["appName"] = app_name
        context.data["appLabel"] = app_label
