import json
from pyblish import api

class CollectClipHandles(api.InstancePlugin):
    """Collect Handles from selected track items."""

    order = api.CollectorOrder + 0.006
    label = "Collect Handles"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

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
