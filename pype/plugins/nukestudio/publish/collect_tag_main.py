from pyblish import api


class CollectClipTagTypes(api.InstancePlugin):
    """Collect Types from Tags of selected track items."""

    order = api.CollectorOrder + 0.012
    label = "Collect main flag"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "plate" in t_family:
                t_subset = t_metadata.get("tag.subset", "")
                subset_name = "{0}{1}".format(
                    t_family,
                    t_subset.capitalize())

                if "plateMain" in subset_name:
                    if not instance.data.get("main"):
                        instance.data["main"] = True
                    self.log.info("`plateMain` found in instance.name: `{}`".format(
                        instance.data["name"]))
        return
