import pyblish.api


class CollectSAAppName(pyblish.api.ContextPlugin):
    """Collect app name and label."""

    label = "Collect App Name/Label"
    order = pyblish.api.CollectorOrder - 0.5
    hosts = ["standalonepublisher"]

    def process(self, context):
        context.data["appName"] = "standalone publisher"
        context.data["appLabel"] = "Standalone publisher"
