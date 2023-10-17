"""
Requires:
    otioTimeline -> context data attribute
    review -> instance data attribute
    masterLayer -> instance data attribute
    otioClipRange -> instance data attribute
"""
from pprint import pformat

import pyblish.api


class CollectOtioFrameRanges(pyblish.api.InstancePlugin):
    """Getting otio ranges from otio_clip

    Adding timeline and source ranges to instance data"""

    label = "Collect OTIO Frame Ranges"
    order = pyblish.api.CollectorOrder - 0.08
    families = ["shot", "clip"]
    hosts = ["resolve", "hiero", "flame", "traypublisher"]

    def process(self, instance):
        # Not all hosts can import these modules.
        import opentimelineio as otio
        from openpype.pipeline.editorial import (
            get_media_range_with_retimes,
            otio_range_to_frame_range,
            otio_range_with_handles
        )

        # get basic variables
        otio_clip = instance.data["otioClip"]
        workfile_start = instance.data["workfileFrameStart"]
        workfile_source_duration = instance.data.get("shotDurationFromSource")

        # get ranges
        otio_tl_range = otio_clip.range_in_parent()
        otio_src_range = otio_clip.source_range
        otio_avalable_range = otio_clip.available_range()
        otio_tl_range_handles = otio_range_with_handles(
            otio_tl_range, instance)
        otio_src_range_handles = otio_range_with_handles(
            otio_src_range, instance)

        # get source avalable start frame
        src_starting_from = otio.opentime.to_frames(
            otio_avalable_range.start_time,
            otio_avalable_range.start_time.rate)

        # convert to frames
        range_convert = otio_range_to_frame_range
        tl_start, tl_end = range_convert(otio_tl_range)
        tl_start_h, tl_end_h = range_convert(otio_tl_range_handles)
        src_start, src_end = range_convert(otio_src_range)
        src_start_h, src_end_h = range_convert(otio_src_range_handles)
        frame_start = workfile_start
        frame_end = frame_start + otio.opentime.to_frames(
            otio_tl_range.duration, otio_tl_range.duration.rate) - 1

        # in case of retimed clip and frame range should not be retimed
        if workfile_source_duration:
            # get available range trimmed with processed retimes
            retimed_attributes = get_media_range_with_retimes(
                otio_clip, 0, 0)
            self.log.debug(
                ">> retimed_attributes: {}".format(retimed_attributes))
            media_in = int(retimed_attributes["mediaIn"])
            media_out = int(retimed_attributes["mediaOut"])
            frame_end = frame_start + (media_out - media_in) + 1
            self.log.debug(frame_end)

        data = {
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "clipIn": tl_start,
            "clipOut": tl_end - 1,
            "clipInH": tl_start_h,
            "clipOutH": tl_end_h - 1,
            "sourceStart": src_starting_from + src_start,
            "sourceEnd": src_starting_from + src_end - 1,
            "sourceStartH": src_starting_from + src_start_h,
            "sourceEndH": src_starting_from + src_end_h - 1,
        }
        instance.data.update(data)
        self.log.debug(
            "_ data: {}".format(pformat(data)))
        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))
