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
            self.log.info("Instance.name: `{}`".format(
                instance.data["name"]))
            # gets tags
            tags = instance.data["tags"]
            assets_shared_a = assets_shared[instance.data["asset"]]
            tag_occurance = 0
            for t in tags:
                t_metadata = dict(t["metadata"])
                t_family = t_metadata.get("tag.family", "")

                # gets only task family tags and collect labels
                if "handles" in t_family:
                    tag_occurance += 1

                    # restore handleStart/End to 0 at first occurance of Tag
                    if tag_occurance == 1:
                        instance.data["handleTag"] = True
                        instance.data["handleStart"] = 0
                        instance.data["handleEnd"] = 0

                    # gets value of handles
                    t_value = int(t_metadata.get("tag.value", ""))

                    # gets arguments if there are any
                    t_args = t_metadata.get("tag.args", "")
                    assert t_args, self.log.error(
                        "Tag with Handles is missing Args. "
                        "Use only handle start/end")

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
                        assets_shared_a[
                            "handleEnd"] = instance.data["handleEnd"]
                    if instance.data.get("handleStart"):
                        assets_shared_a[
                            "handleStart"] = instance.data["handleStart"]
