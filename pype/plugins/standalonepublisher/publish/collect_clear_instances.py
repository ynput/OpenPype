"""
Optional:
    instance.data["remove"]     -> mareker for removing
"""
import pyblish.api


class CollectClearInstances(pyblish.api.ContextPlugin):
    """Clear all marked instances"""

    order = pyblish.api.CollectorOrder + 0.4999
    label = "Clear Instances"
    hosts = ["standalonepublisher"]

    def process(self, context):

        for instance in context:
            if instance.data.get("remove"):
                self.log.info(f"Removing: {instance}")
                context.remove(instance)
