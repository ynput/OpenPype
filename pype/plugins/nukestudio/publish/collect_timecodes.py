import pyblish.api
import opentimelineio.opentime as otio_ot


class CollectClipTimecodes(pyblish.api.InstancePlugin):
    """Collect time with OpenTimelineIO:
        source_h(In,Out)[timecode, sec]
        timeline(In,Out)[timecode, sec]
    """

    order = pyblish.api.CollectorOrder + 0.101
    label = "Collect Timecodes"
    hosts = ["nukestudio"]

    def process(self, instance):

        data = dict()
        self.log.debug("__ instance.data: {}".format(instance.data))
        # Timeline data.
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        source_in_h = instance.data("sourceInH",
                                    instance.data("sourceIn") - handle_start)
        source_out_h = instance.data("sourceOutH",
                                     instance.data("sourceOut") + handle_end)

        timeline_in = instance.data["clipIn"]
        timeline_out = instance.data["clipOut"]

        # set frame start with tag or take it from timeline
        frame_start = instance.data.get("startingFrame")

        if not frame_start:
            frame_start = timeline_in

        source = instance.data.get("source")

        otio_data = dict()
        self.log.debug("__ source: `{}`".format(source))

        rate_fps = instance.context.data["fps"]

        otio_in_h_ratio = otio_ot.RationalTime(
            value=(source.timecodeStart() + (
                source_in_h + (source_out_h - source_in_h))),
            rate=rate_fps)

        otio_out_h_ratio = otio_ot.RationalTime(
            value=(source.timecodeStart() + source_in_h),
            rate=rate_fps)

        otio_timeline_in_ratio = otio_ot.RationalTime(
            value=int(
                instance.data.get("timelineTimecodeStart", 0)) + timeline_in,
            rate=rate_fps)

        otio_timeline_out_ratio = otio_ot.RationalTime(
            value=int(
                instance.data.get("timelineTimecodeStart", 0)) + timeline_out,
            rate=rate_fps)

        otio_data.update({

            "otioClipInHTimecode": otio_ot.to_timecode(otio_in_h_ratio),

            "otioClipOutHTimecode": otio_ot.to_timecode(otio_out_h_ratio),

            "otioClipInHSec": otio_ot.to_seconds(otio_in_h_ratio),

            "otioClipOutHSec": otio_ot.to_seconds(otio_out_h_ratio),

            "otioTimelineInTimecode": otio_ot.to_timecode(
                otio_timeline_in_ratio),

            "otioTimelineOutTimecode": otio_ot.to_timecode(
                otio_timeline_out_ratio),

            "otioTimelineInSec": otio_ot.to_seconds(otio_timeline_in_ratio),

            "otioTimelineOutSec": otio_ot.to_seconds(otio_timeline_out_ratio)
        })

        data.update({
            "otioData": otio_data,
            "sourceTimecodeIn": otio_ot.to_timecode(otio_in_h_ratio),
            "sourceTimecodeOut": otio_ot.to_timecode(otio_out_h_ratio)
        })
        instance.data.update(data)
        self.log.debug("data: {}".format(instance.data))
