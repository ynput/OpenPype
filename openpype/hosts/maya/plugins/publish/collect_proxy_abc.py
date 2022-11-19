import pyblish.api

class CollectProxyAlembic(pyblish.api.InstancePlugin):
    """Collect Proxy Alembic for instance."""

    order = pyblish.api.CollectorOrder + 0.45
    families = ["proxyAbc"]
    label = "Collect Proxy Alembic"
    hosts = ["maya"]

    def process(self, instance):
        """Collector entry point."""
        if not instance.data.get('families'):
            instance.data["families"] = []
