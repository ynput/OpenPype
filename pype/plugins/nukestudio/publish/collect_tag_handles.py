import json
from pyblish import api


class CollectClipTagHandles(api.ContextPlugin):
    """Collect Handles from selected track items."""

    order = api.CollectorOrder + 0.012
    label = "Collect Tag Handles"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, context):
        assets_shared = context.data.get("assetsShared")
        for instance in context[:]:
            # gets tags
            tags = instance.data["tags"]
            assets_shared_a = assets_shared[instance.data["asset"]]
            for t in tags:
                t_metadata = dict(t["metadata"])
                t_family = t_metadata.get("tag.family", "")

                # gets only task family tags and collect labels
                if "handles" in t_family:
                    # gets value of handles
                    t_value = int(t_metadata.get("tag.value", ""))

                    # gets arguments if there are any
                    t_args = t_metadata.get("tag.args", "")

                    # distribute handles
                    if not t_args:
                        # add handles to both sides
                        instance.data['handles'] = t_value
                        self.log.info("Collected Handles: `{}`".format(
                            instance.data['handles']))
                    else:
                        t_args = json.loads(t_args.replace("'", "\""))
                        # add in start
                        if 'start' in t_args['where']:
                            instance.data["handleStart"] += t_value
                            self.log.info("Collected Handle Start: `{}`".format(
                                instance.data["handleStart"]))

                        # add in end
                        if 'end' in t_args['where']:
                            instance.data["handleEnd"] += t_value
                            self.log.info("Collected Handle End: `{}`".format(
                                instance.data["handleEnd"]))

                    # adding handles to asset_shared on context
                    if instance.data.get("handleEnd"):
                        assets_shared_a["handleEnd"] = instance.data["handleEnd"]
                    if instance.data.get("handleStart"):
                        assets_shared_a["handleStart"] = instance.data["handleStart"]
                    if instance.data.get("handles"):
                        assets_shared_a["handles"] = instance.data["handles"]
