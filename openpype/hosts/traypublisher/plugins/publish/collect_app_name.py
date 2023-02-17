import pyblish.api


class CollectTrayPublisherAppName(pyblish.api.ContextPlugin):
    """Collect app name and label."""

    label = "Collect App Name/Label"
    order = pyblish.api.CollectorOrder - 0.5
    hosts = ["traypublisher"]

    def process(self, context):
        context.data["appName"] = "tray publisher"
        context.data["appLabel"] = "Tray publisher"
