import pyblish.api


class CollectClipFrameRanges(pyblish.api.InstancePlugin):
    """Collect all frame range data"""

    order = pyblish.api.CollectorOrder + 0.101
    label = "Collect Frame Ranges"
    hosts = ["standalonepublisher"]
    families = ["clip"]

    # presets
    start_frame_offset = None  # if 900000 for edl default then -900000
    custom_start_frame = 1

    def process(self, instance):

        data = dict()

        # Timeline data.
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        source_in_h = instance.data("sourceInH",
                                    instance.data("sourceIn") - handle_start)
        source_out_h = instance.data("sourceOutH",
                                     instance.data("sourceOut") + handle_end)

        timeline_in = instance.data["clipIn"]
        timeline_out = instance.data["clipOut"]

        timeline_in_h = timeline_in - handle_start
        timeline_out_h = timeline_out + handle_end

        # define starting frame for future shot
        frame_start = self.custom_start_frame or timeline_in

        # add offset in case there is any
        if self.start_frame_offset:
            frame_start += self.start_frame_offset

        frame_end = frame_start + (timeline_out - timeline_in)

        data.update({
            "sourceInH": source_in_h,
            "sourceOutH": source_out_h,
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "clipInH": timeline_in_h,
            "clipOutH": timeline_out_h,
            "clipDurationH": instance.data.get(
                "clipDuration") + handle_start + handle_end
            }
        )
        self.log.debug("__ data: {}".format(data))
        instance.data.update(data)
