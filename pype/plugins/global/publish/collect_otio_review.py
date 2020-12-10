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
        otio_timeline = instance.context.data["otioTimeline"]
        otio_clip = instance.data["otioClip"]
        otio_tl_range = otio_clip.range_in_parent()

        # skip if master layer is False
        if not master_layer:
            return

        for track in otio_timeline.tracks:
            if review_track_name not in track.name:
                continue
            otio_review_clips = otio.algorithms.track_trimmed_to_range(
                track,
                otio_tl_range
            )

        instance.data["otioReviewClips"] = otio_review_clips
        self.log.debug(
            "_ otio_review_clips: {}".format(otio_review_clips))

        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))
