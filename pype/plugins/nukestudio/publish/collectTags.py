from pyblish import api


class CollectTrackItemTags(api.InstancePlugin):
    """Collect Tags from selected track items."""

    order = api.CollectorOrder
    label = "Collect Tags"
    hosts = ["nukestudio"]

    def process(self, instance):
        instance.data["tags"] = instance.data["item"].tags()
        self.log.info(instance.data["tags"])
        return
