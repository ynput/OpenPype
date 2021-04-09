"""
Requires:
    instance -> otioClip
    context -> otioTimeline

Optional:
    otioClip.metadata -> masterLayer

Provides:
    instance -> otioReviewClips
    instance -> families (adding ["review", "ftrack"])
"""

import opentimelineio as otio
import pyblish.api
from pprint import pformat


class CollectOcioReview(pyblish.api.InstancePlugin):
    """Get matching otio track from defined review layer"""

    label = "Collect OTIO Review"
    order = pyblish.api.CollectorOrder - 0.57
    families = ["clip"]
    hosts = ["resolve", "hiero"]

    def process(self, instance):
        # get basic variables
        otio_review_clips = list()
        otio_timeline = instance.context.data["otioTimeline"]
        otio_clip = instance.data["otioClip"]

        # optionally get `reviewTrack`
        review_track_name = otio_clip.metadata.get("reviewTrack")

        # generate range in parent
        otio_tl_range = otio_clip.range_in_parent()

        # calculate real timeline end needed for the clip
        clip_end_frame = int(
            otio_tl_range.start_time.value + otio_tl_range.duration.value)

        # skip if no review track available
        if not review_track_name:
            return

        # loop all tracks and match with name in `reviewTrack`
        for track in otio_timeline.tracks:
            if review_track_name not in track.name:
                continue

            # process correct track
            # establish gap
            otio_gap = None

            # get track parent range
            track_rip = track.range_in_parent()

            # calculate real track end frame
            track_end_frame = int(
                track_rip.start_time.value + track_rip.duration.value)

            # check if the end of track is not lower then clip requirement
            if clip_end_frame > track_end_frame:
                # calculate diference duration
                gap_duration = clip_end_frame - track_end_frame
                # create rational time range for gap
                otio_gap_range = otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(
                        float(0),
                        track_rip.start_time.rate
                    ),
                    duration=otio.opentime.RationalTime(
                        float(gap_duration),
                        track_rip.start_time.rate
                    )
                )
                # crate gap
                otio_gap = otio.schema.Gap(source_range=otio_gap_range)

            # trim available clips from devined track as reviewable source
            otio_review_clips = otio.algorithms.track_trimmed_to_range(
                track,
                otio_tl_range
            )
            # add gap at the end if track end is shorter then needed
            if otio_gap:
                otio_review_clips.append(otio_gap)

        if otio_review_clips:
            instance.data["families"] += ["review", "ftrack"]
            instance.data["otioReviewClips"] = otio_review_clips
            self.log.info(
                "Creating review track: {}".format(otio_review_clips))

        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))
        self.log.debug(
            "_ families: {}".format(instance.data["families"]))
