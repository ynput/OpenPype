import pyblish.api


class CollectInstanceData(pyblish.api.InstancePlugin):
    """Collect Fusion saver instances

    This additionally stores the Comp start and end render range in the
    current context's data as "frameStart" and "frameEnd".

    """

    order = pyblish.api.CollectorOrder
    label = "Collect Instances Data"
    hosts = ["fusion"]

    def process(self, instance):
        """Collect all image sequence tools"""

        context = instance.context

        # Include creator attributes directly as instance data
        creator_attributes = instance.data["creator_attributes"]
        instance.data.update(creator_attributes)

        # get asset frame ranges
        start = context.data["frameStart"]
        end = context.data["frameEnd"]
        handle_start = context.data["handleStart"]
        handle_end = context.data["handleEnd"]
        start_handle = start - handle_start
        end_handle = end + handle_end

        if creator_attributes.get("custom_range"):
            # get comp frame ranges
            start = context.data["renderFrameStart"]
            end = context.data["renderFrameEnd"]
            handle_start = 0
            handle_end = 0
            start_handle = start
            end_handle = end

        # Include start and end render frame in label
        subset = instance.data["subset"]
        label = "{subset} ({start}-{end})".format(subset=subset,
                                                  start=int(start),
                                                  end=int(end))

        instance.data.update({
            "label": label,

            # todo: Allow custom frame range per instance
            "frameStart": start,
            "frameEnd": end,
            "frameStartHandle": start_handle,
            "frameEndHandle": end_handle,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "fps": context.data["fps"],
        })

        # Add review family if the instance is marked as 'review'
        # This could be done through a 'review' Creator attribute.
        if instance.data.get("review", False):
            self.log.info("Adding review family..")
            instance.data["families"].append("review")
