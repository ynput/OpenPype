import pyblish.api


class CollectFrameRanges(pyblish.api.InstancePlugin):
    """ Collect all framranges.
    """

    order = pyblish.api.CollectorOrder
    label = "Collect Frame Ranges"
    hosts = ["hiero"]
    families = ["clip", "effect"]

    def process(self, instance):

        data = dict()
        track_item = instance.data["item"]

        # handles
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # source frame ranges
        source_in = int(track_item.sourceIn())
        source_out = int(track_item.sourceOut())
        source_in_h = int(source_in - handle_start)
        source_out_h = int(source_out + handle_end)

        # timeline frame ranges
        clip_in = int(track_item.timelineIn())
        clip_out = int(track_item.timelineOut())
        clip_in_h = clip_in - handle_start
        clip_out_h = clip_out + handle_end

        # durations
        clip_duration = (clip_out - clip_in) + 1
        clip_duration_h = clip_duration + (handle_start + handle_end)

        # set frame start with tag or take it from timeline `startingFrame`
        frame_start = instance.data.get("workfileFrameStart")

        if not frame_start:
            frame_start = clip_in

        frame_end = frame_start + (clip_out - clip_in)

        data.update({
            # media source frame range
            "sourceIn": source_in,
            "sourceOut": source_out,
            "sourceInH": source_in_h,
            "sourceOutH": source_out_h,

            # timeline frame range
            "clipIn": clip_in,
            "clipOut": clip_out,
            "clipInH": clip_in_h,
            "clipOutH": clip_out_h,

            # workfile frame range
            "frameStart": frame_start,
            "frameEnd": frame_end,

            "clipDuration": clip_duration,
            "clipDurationH": clip_duration_h,

            "fps": instance.context.data["fps"]
        })
        self.log.info("Frame range data for instance `{}` are: {}".format(
            instance, data))
        instance.data.update(data)
