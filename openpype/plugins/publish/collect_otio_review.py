"""
Requires:
    instance -> otioClip
    context -> otioTimeline

Optional:
    instance -> reviewTrack

Provides:
    instance -> otioReviewClips
    instance -> families (adding ["review", "ftrack"])
"""

import opentimelineio as otio
import pyblish.api
from pprint import pformat


class CollectOtioReview(pyblish.api.InstancePlugin):
    """Get matching otio track from defined review layer"""

    label = "Collect OTIO Review"
    order = pyblish.api.CollectorOrder - 0.078
    families = ["clip"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, instance):
        # get basic variables
        otio_review_clips = []
        otio_timeline = instance.context.data["otioTimeline"]
        otio_clip = instance.data["otioClip"]
        self.log.debug("__ otioClip: {}".format(otio_clip))
        # optionally get `reviewTrack`
        review_track_name = instance.data.get("reviewTrack")

        # generate range in parent
        otio_tl_range = otio_clip.range_in_parent()

        # calculate real timeline end needed for the clip
        clip_frame_end = int(
            otio_tl_range.start_time.value + otio_tl_range.duration.value)

        # skip if no review track available
        if not review_track_name:
            return

        # loop all tracks and match with name in `reviewTrack`
        for track in otio_timeline.tracks:
            if review_track_name != track.name:
                continue

            # process correct track
            # establish gap
            otio_gap = None

            # get track parent range
            track_rip = track.range_in_parent()

            # calculate real track end frame
            track_frame_end = int(track_rip.end_time_exclusive().value)

            # check if the end of track is not lower then clip requirement
            if clip_frame_end > track_frame_end:
                # calculate diference duration
                gap_duration = clip_frame_end - track_frame_end
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
            instance.data["label"] += " (review)"
            instance.data["families"] += ["review", "ftrack"]
            instance.data["otioReviewClips"] = otio_review_clips
            self.log.info(
                "Creating review track: {}".format(otio_review_clips))

        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))
        self.log.debug(
            "_ families: {}".format(instance.data["families"]))
