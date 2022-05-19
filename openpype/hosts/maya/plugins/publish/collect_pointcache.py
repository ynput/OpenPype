import pyblish.api


class CollectPointcache(pyblish.api.InstancePlugin):
    """Collect pointcache data for instance."""

    order = pyblish.api.CollectorOrder + 0.4
    families = ["pointcache"]
    label = "Collect Pointcache"
    hosts = ["maya"]

    def process(self, instance):
        if instance.data.get("farm"):
            instance.data["families"].append("deadline")