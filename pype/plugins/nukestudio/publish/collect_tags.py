from pyblish import api


class CollectClipTags(api.InstancePlugin):
    """Collect Tags from selected track items."""

    order = api.CollectorOrder + 0.011
    label = "Collect Tags"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        tags = instance.data["item"].tags()

        tags_d = []
        if tags:
            for t in tags:
                tag_data = {
                    "name": t.name(),
                    "object": t,
                    "metadata": t.metadata(),
                    "inTime": t.inTime(),
                    "outTime": t.outTime(),
                }
                tags_d.append(tag_data)

        instance.data["tags"] = tags_d

        self.log.info(instance.data["tags"])
        return
