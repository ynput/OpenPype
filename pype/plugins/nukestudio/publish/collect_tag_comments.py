from pyblish import api


class CollectClipTagComments(api.InstancePlugin):
    """Collect comments from tags on selected track items and their sources."""

    order = api.CollectorOrder + 0.013
    label = "Collect Comments"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, instance):
        # Collect comments.
        instance.data["comments"] = []

        # Exclude non-tagged instances.
        for tag in instance.data["tags"]:
            if tag["name"].lower() == "comment":
                instance.data["comments"].append(
                    tag["metadata"]["tag.note"]
                )

        # Find tags on the source clip.
        tags = instance.data["item"].source().tags()
        for tag in tags:
            if tag.name().lower() == "comment":
                instance.data["comments"].append(
                    tag.metadata().dict()["tag.note"]
                )

        # Update label with comments counter.
        instance.data["label"] = "{} - comments:{}".format(
            instance.data["label"],
            len(instance.data["comments"])
        )
