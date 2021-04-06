"""
Optional:
    instance.data["remove"]     -> mareker for removing
"""
import pyblish.api


class CollectClearInstances(pyblish.api.InstancePlugin):
    """Clear all marked instances"""

    order = pyblish.api.CollectorOrder + 0.4999
    label = "Clear Instances"
    hosts = ["standalonepublisher"]

    def process(self, instance):
        self.log.debug(
            f"Instance: `{instance}` | "
            f"families: `{instance.data['families']}`")
        if instance.data.get("remove"):
            self.log.info(f"Removing: {instance}")
            instance.context.remove(instance)
