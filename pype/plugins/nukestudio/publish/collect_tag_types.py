from pyblish import api


class CollectClipTagTypes(api.InstancePlugin):
    """Collect Types from Tags of selected track items."""

    order = api.CollectorOrder + 0.007
    label = "Collect Plate Type from Tag"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        subset_names = list()
        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "plate" in t_family:
                t_type = t_metadata.get("tag.type", "")
                t_order = t_metadata.get("tag.order", "")
                subset_type = "{0}{1}".format(
                    t_type.capitalize(), t_order)
                subset_names.append(subset_type)

                if "main" in t_type:
                    instance.data["main"] = True

        if subset_names:
            instance.data["subsetType"] = subset_names[0]

        self.log.info("Collected Plate Types from Tags: `{}`".format(
            instance.data["subsetType"]))
        return
