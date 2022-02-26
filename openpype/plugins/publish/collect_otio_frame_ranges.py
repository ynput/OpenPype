"""
Requires:
    otioTimeline -> context data attribute
    review -> instance data attribute
    masterLayer -> instance data attribute
    otioClipRange -> instance data attribute
"""
# import os
import opentimelineio as otio
import pyblish.api
import openpype.lib
from pprint import pformat


class CollectOtioFrameRanges(pyblish.api.InstancePlugin):
    """Getting otio ranges from otio_clip

    Adding timeline and source ranges to instance data"""

    label = "Collect OTIO Frame Ranges"
    order = pyblish.api.CollectorOrder - 0.08
    families = ["shot", "clip"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, instance):
        # get basic variables
        otio_clip = instance.data["otioClip"]
        workfile_start = instance.data["workfileFrameStart"]

        # get ranges
        otio_tl_range = otio_clip.range_in_parent()
        otio_src_range = otio_clip.source_range
        otio_avalable_range = otio_clip.available_range()
        otio_tl_range_handles = openpype.lib.otio_range_with_handles(
            otio_tl_range, instance)
        otio_src_range_handles = openpype.lib.otio_range_with_handles(
            otio_src_range, instance)

        # get source avalable start frame
        src_starting_from = otio.opentime.to_frames(
            otio_avalable_range.start_time,
            otio_avalable_range.start_time.rate)

        # convert to frames
        range_convert = openpype.lib.otio_range_to_frame_range
        tl_start, tl_end = range_convert(otio_tl_range)
        tl_start_h, tl_end_h = range_convert(otio_tl_range_handles)
        src_start, src_end = range_convert(otio_src_range)
        src_start_h, src_end_h = range_convert(otio_src_range_handles)
        frame_start = workfile_start
        frame_end = frame_start + otio.opentime.to_frames(
            otio_tl_range.duration, otio_tl_range.duration.rate) - 1

        data = {
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "clipIn": tl_start,
            "clipOut": tl_end,
            "clipInH": tl_start_h,
            "clipOutH": tl_end_h,
            "sourceStart": src_starting_from + src_start,
            "sourceEnd": src_starting_from + src_end,
            "sourceStartH": src_starting_from + src_start_h,
            "sourceEndH": src_starting_from + src_end_h,
        }
        instance.data.update(data)
        self.log.debug(
            "_ data: {}".format(pformat(data)))
        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))
