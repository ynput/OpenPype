from pyblish import api


class CollectTagRetime(api.InstancePlugin):
    """Collect Retiming from Tags of selected track items."""

    order = api.CollectorOrder + 0.014
    label = "Collect Retiming Tag"
    hosts = ["hiero"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "retiming" in t_family:
                margin_in = t_metadata.get("tag.marginIn", "")
                margin_out = t_metadata.get("tag.marginOut", "")

                instance.data["retimeMarginIn"] = int(margin_in)
                instance.data["retimeMarginOut"] = int(margin_out)
                instance.data["retime"] = True

                self.log.info("retimeMarginIn: `{}`".format(margin_in))
                self.log.info("retimeMarginOut: `{}`".format(margin_out))

                instance.data["families"] += ["retime"]
