from pyblish import api


class CollectClipSubsetsTags(api.InstancePlugin):
    """Collect Subsets from Tags of selected track items."""

    order = api.CollectorOrder + 0.012
    label = "Collect Tags Subsets"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", None)
            t_subset = t_metadata.get("tag.subset", None)

            # gets only task family tags and collect labels
            if t_subset and t_family:
                subset_name = "{0}{1}".format(
                    t_family,
                    t_subset.capitalize())
                instance.data['subset'] = subset_name

                self.log.info("`subset`: {0} found in `instance.name`: `{1}`".format(subset_name, instance.data["name"]))
