import pyblish.api


class CollectReview(pyblish.api.InstancePlugin):
    """Collect review instance from rendered frames
    """

    order = pyblish.api.CollectorOrder + 0.3
    family = "review"
    label = "Collect Review"
    hosts = ["nuke"]
    families = ["render", "render.local"]

    def process(self, instance):
        if instance.data["families"]:
            instance.data["families"].append("review")
            self.log.info("Review collected: `{}`".format(instance))
