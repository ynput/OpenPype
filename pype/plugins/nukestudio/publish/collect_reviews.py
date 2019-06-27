from pyblish import api


class CollectReviews(api.InstancePlugin):
    """Collect review from tags.

    Tag is expected to have metadata:
        {
            "family": "review"
            "subset": "main"
        }
    """

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1025
    label = "Collect Reviews"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, instance):
        # Exclude non-tagged instances.
        tagged = False
        for tag in instance.data["tags"]:
            family = dict(tag["metadata"]).get("tag.family", "")
            if family.lower() == "review":
                tagged = True

        if not tagged:
            self.log.debug(
                "Skipping \"{}\" because its not tagged with "
                "\"review\"".format(instance)
            )
            return

        # Collect data.
        data = {}
        for key, value in instance.data.iteritems():
            data[key] = value

        data["family"] = "review"
        data["ftrackFamily"] = "img"
        data["families"] = ["ftrack"]

        subset = ""
        for tag in instance.data["tags"]:
            tag_data = dict(tag["metadata"])
            if "tag.subset" in tag_data:
                subset = tag_data["tag.subset"]
        data["subset"] = subset

        data["source"] = data["sourcePath"]

        self.log.debug("Creating instance with data: {}".format(data))
        instance.context.create_instance(**data)
