import pyblish.api


class CollectClipFrameRanges(pyblish.api.InstancePlugin):
    """Collect all frame range data: source(In,Out), timeline(In,Out), edit_(in, out), f(start, end)"""

    order = pyblish.api.CollectorOrder + 0.101
    label = "Collect Frame Ranges"
    hosts = ["nukestudio"]

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

        # set frame start with tag or take it from timeline
        frame_start = instance.data.get("startingFrame")

        if not frame_start:
            frame_start = timeline_in

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
