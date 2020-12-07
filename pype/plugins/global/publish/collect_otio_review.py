"""
Requires:
    otioTimeline -> context data attribute
    review -> instance data attribute
    masterLayer -> instance data attribute
    otioClipRange -> instance data attribute
"""
import opentimelineio as otio
import pyblish.api
from pype.lib import (
    is_overlapping,
    convert_otio_range_to_frame_range
)


class CollectOcioReview(pyblish.api.InstancePlugin):
    """Get matching otio from defined review layer"""

    label = "Collect OTIO review"
    order = pyblish.api.CollectorOrder
    families = ["clip"]
    hosts = ["resolve"]

    def process(self, instance):
        # get basic variables
        review_track_name = instance.data["review"]
        master_layer = instance.data["masterLayer"]
        otio_timeline_context = instance.context.data["otioTimeline"]
        otio_clip_range = instance.data["otioClipRange"]

        # skip if master layer is False
        if not master_layer:
            return

        for otio_clip in otio_timeline_context.each_clip():
            track_name = otio_clip.parent().name
            parent_range = otio_clip.range_in_parent()
            if track_name not in review_track_name:
                continue
            if isinstance(otio_clip, otio.schema.Clip):
                if is_overlapping(parent_range, otio_clip_range, strict=False):
                    self.create_representation(
                        otio_clip, otio_clip_range, instance)

    def create_representation(self, otio_clip, to_otio_range, instance):
        to_timeline_start, to_timeline_end = convert_otio_range_to_frame_range(
            to_otio_range)
        timeline_start, timeline_end = convert_otio_range_to_frame_range(
            otio_clip.range_in_parent())
        source_start, source_end = convert_otio_range_to_frame_range(
            otio_clip.source_range)
        media_reference = otio_clip.media_reference
        available_start, available_end = convert_otio_range_to_frame_range(
            media_reference.available_range)
        path = media_reference.target_url
        self.log.debug(path)
        self.log.debug((available_start, available_end))
        self.log.debug((source_start, source_end))
        self.log.debug((timeline_start, timeline_end))
        self.log.debug((to_timeline_start, to_timeline_end))
