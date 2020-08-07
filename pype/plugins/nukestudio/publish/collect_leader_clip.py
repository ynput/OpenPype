from pyblish import api


class CollectLeaderClip(api.InstancePlugin):
    """Collect Leader clip from selected track items. Clip with hierarchy Tag is defining sharable data attributes between other clips with `subset` tags. So `handle_start/end`, `frame_start`, etc"""

    order = api.CollectorOrder + 0.0111
    label = "Collect Leader Clip"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        for t in tags:
            t_metadata = dict(t["metadata"])
            t_type = t_metadata.get("tag.label", "")
            self.log.info("`hierarhy`: `{}`".format(t_type))
            # gets only task family tags and collect labels
            if "hierarchy" in t_type.lower():
                if not instance.data.get("main"):
                    instance.data["main"] = True
                self.log.info("`Leader Clip` found in instance.name: `{}`".format(instance.data["name"]))
