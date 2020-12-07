"""
Requires:
    otioTimeline -> context data attribute
    review -> instance data attribute
    masterLayer -> instance data attribute
    otioClip -> instance data attribute
    otioClipRange -> instance data attribute
"""
import opentimelineio as otio
from opentimelineio.opentime import to_frames
import pyblish.api


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
        otio_timeline_context = instance.context.data.get("otioTimeline")
        otio_clip = instance.data["otioClip"]
        otio_clip_range = instance.data["otioClipRange"]

        # skip if master layer is False
        if not master_layer:
            return

        # get timeline time values
        start_time = otio_timeline_context.global_start_time
        timeline_fps = start_time.rate
        playhead = start_time.value

        frame_start = to_frames(
            otio_clip_range.start_time, timeline_fps)
        frame_duration = to_frames(
            otio_clip_range.duration, timeline_fps)
        self.log.debug(
            ("name: {} | "
             "timeline_in: {} | timeline_out: {}").format(
                otio_clip.name, frame_start,
                (frame_start + frame_duration - 1)))

        orwc_fps = timeline_fps
        for otio_clip in otio_timeline_context.each_clip():
            track_name = otio_clip.parent().name
            if track_name not in review_track_name:
                continue
            if isinstance(otio_clip, otio.schema.Clip):
                orwc_source_range = otio_clip.source_range
                orwc_fps = orwc_source_range.start_time.rate
                orwc_start = to_frames(orwc_source_range.start_time, orwc_fps)
                orwc_duration = to_frames(orwc_source_range.duration, orwc_fps)
                source_in = orwc_start
                source_out = (orwc_start + orwc_duration) - 1
                timeline_in = playhead
                timeline_out = (timeline_in + orwc_duration) - 1
                self.log.debug(
                    ("name: {} | source_in: {} | source_out: {} | "
                     "timeline_in: {} | timeline_out: {} "
                     "| orwc_fps: {}").format(
                        otio_clip.name, source_in, source_out,
                        timeline_in, timeline_out, orwc_fps))

                # move plyhead to next available frame
                playhead = timeline_out + 1

            elif isinstance(otio_clip, otio.schema.Gap):
                gap_source_range = otio_clip.source_range
                gap_fps = gap_source_range.start_time.rate
                gap_start = to_frames(
                    gap_source_range.start_time, gap_fps)
                gap_duration = to_frames(
                    gap_source_range.duration, gap_fps)
                if gap_fps != orwc_fps:
                    gap_duration += 1
                self.log.debug(
                    ("name: Gap | gap_start: {} | gap_fps: {}"
                     "| gap_duration: {} | timeline_fps: {}").format(
                        gap_start, gap_fps, gap_duration, timeline_fps))
                playhead += gap_duration
