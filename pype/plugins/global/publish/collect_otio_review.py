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
import pype.lib
from pprint import pformat


class CollectOcioReview(pyblish.api.InstancePlugin):
    """Get matching otio from defined review layer"""

    label = "Collect OTIO review"
    order = pyblish.api.CollectorOrder - 0.57
    families = ["clip"]
    hosts = ["resolve"]

    def process(self, instance):
        otio_review_clips = list()
        # get basic variables
        review_track_name = instance.data["review"]
        master_layer = instance.data["masterLayer"]
        otio_timeline_context = instance.context.data["otioTimeline"]
        otio_clip = instance.data["otioClip"]
        otio_clip_range = otio_clip.range_in_parent()
        # skip if master layer is False
        if not master_layer:
            return

        for _otio_clip in otio_timeline_context.each_clip():
            track_name = _otio_clip.parent().name
            parent_range = _otio_clip.range_in_parent()
            if track_name not in review_track_name:
                continue
            if isinstance(_otio_clip, otio.schema.Clip):
                test_start, test_end = pype.lib.otio_range_to_frame_range(
                    parent_range)
                main_start, main_end = pype.lib.otio_range_to_frame_range(
                    otio_clip_range)
                if pype.lib.is_overlapping_otio_ranges(
                        parent_range, otio_clip_range, strict=False):
                    # add found clips to list
                    otio_review_clips.append(_otio_clip)

        instance.data["otioReviewClips"] = otio_review_clips
        self.log.debug(
            "_ otio_review_clips: {}".format(otio_review_clips))

        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))
