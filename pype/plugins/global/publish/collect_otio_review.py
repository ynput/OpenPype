"""
Requires:
    otioTimeline -> context data attribute
    review -> instance data attribute
    masterLayer -> instance data attribute
    otioClipRange -> instance data attribute
"""
import os
import opentimelineio as otio
import pyblish.api
import pype.lib


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
                if pype.lib.is_overlapping_otio_ranges(
                        parent_range, otio_clip_range, strict=False):
                    self.create_representation(
                        _otio_clip, otio_clip_range, instance)

    def create_representation(self, otio_clip, to_otio_range, instance):
        to_tl_start, to_tl_end = pype.lib.convert_otio_range_to_frame_range(
            to_otio_range)
        tl_start, tl_end = pype.lib.convert_otio_range_to_frame_range(
            otio_clip.range_in_parent())
        source_start, source_end = pype.lib.convert_otio_range_to_frame_range(
            otio_clip.source_range)
        media_reference = otio_clip.media_reference
        metadata = media_reference.metadata
        mr_start, mr_end = pype.lib.convert_otio_range_to_frame_range(
            media_reference.available_range)
        path = media_reference.target_url
        reference_frame_start = (mr_start + source_start) + (
            to_tl_start - tl_start)
        reference_frame_end = (mr_start + source_end) - (
            tl_end - to_tl_end)

        base_name = os.path.basename(path)
        staging_dir = os.path.dirname(path)
        ext = os.path.splitext(base_name)[1][1:]

        if metadata.get("isSequence"):
            files = list()
            padding = metadata["padding"]
            base_name = pype.lib.convert_to_padded_path(base_name, padding)
            for index in range(
                    reference_frame_start, (reference_frame_end + 1)):
                file_name = base_name % index
                path_test = os.path.join(staging_dir, file_name)
                if os.path.exists(path_test):
                    files.append(file_name)

            self.log.debug(files)
        else:
            files = base_name

        representation = {
            "ext": ext,
            "name": ext,
            "files": files,
            "frameStart": reference_frame_start,
            "frameEnd": reference_frame_end,
            "stagingDir": staging_dir
        }
        self.log.debug(representation)
