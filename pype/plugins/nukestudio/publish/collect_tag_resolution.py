from pyblish import api


class CollectClipTagResolution(api.InstancePlugin):
    """Collect Source Resolution from Tags of selected track items."""

    order = api.CollectorOrder + 0.013
    label = "Collect Source Resolution"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "resolution" in t_family:
                instance.data["sourceResolution"] = True
