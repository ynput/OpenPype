"""
Requires:
    instance -> review
    instance -> masterLayer
    instance -> otioClip
    context -> otioTimeline

Provides:
    instance -> otioReviewClips
"""

import clique
import opentimelineio as otio
import pyblish.api
import pype


class CollectOcioSubsetResources(pyblish.api.InstancePlugin):
    """Get Resources for a subset version"""

    label = "Collect OTIO Subset Resources"
    order = pyblish.api.CollectorOrder - 0.57
    families = ["clip"]
    hosts = ["resolve"]

    def process(self, instance):
        # get basic variables
        otio_clip = instance.data["otioClip"]

        # generate range in parent
        otio_src_range = otio_clip.source_range
        otio_avalable_range = otio_clip.available_range()
        otio_visible_range = otio_clip.visible_range()
        otio_src_range_handles = pype.lib.otio_range_with_handles(
            otio_src_range, instance)
        trimmed_media_range = pype.lib.trim_media_range(
            otio_avalable_range, otio_src_range_handles)

        self.log.debug(
            "_ otio_avalable_range: {}".format(otio_avalable_range))
        self.log.debug(
            "_ otio_visible_range: {}".format(otio_visible_range))
        self.log.debug(
            "_ otio_src_range: {}".format(otio_src_range))
        self.log.debug(
            "_ otio_src_range_handles: {}".format(otio_src_range_handles))
        self.log.debug(
            "_ trimmed_media_range: {}".format(trimmed_media_range))

        #
        # media_ref = otio_clip.media_reference
        # metadata = media_ref.metadata
        #
        # if isinstance(media_ref, otio.schema.ImageSequenceReference):
        #     dirname = media_ref.target_url_base
        #     head = media_ref.name_prefix
        #     tail = media_ref.name_suffix
        #     first, last = pype.lib.otio_range_to_frame_range(
        #         available_range)
        #     collection = clique.Collection(
        #         head=head,
        #         tail=tail,
        #         padding=media_ref.frame_zero_padding
        #     )
        #     collection.indexes.update(
        #         [i for i in range(first, (last + 1))])
        #     # render segment
        #     self._render_seqment(
        #         sequence=[dirname, collection])
        #     # generate used frames
        #     self._generate_used_frames(
        #         len(collection.indexes))
        # elif metadata.get("padding"):
        #     # in case it is file sequence but not new OTIO schema
        #     # `ImageSequenceReference`
        #     path = media_ref.target_url
        #     dir_path, collection = self._make_sequence_collection(
        #         path, available_range, metadata)
        #
        #     # render segment
        #     self._render_seqment(
        #         sequence=[dir_path, collection])
        #     # generate used frames
        #     self._generate_used_frames(
        #         len(collection.indexes))
        # else:
        #     path = media_ref.target_url
        #     # render video file to sequence
        #     self._render_seqment(
        #         video=[path, available_range])
        #     # generate used frames
        #     self._generate_used_frames(
        #         available_range.duration.value)
        #
        # instance.data["otioReviewClips"] = otio_review_clips
        # self.log.debug(
        #     "_ otio_review_clips: {}".format(otio_review_clips))
        #
        # self.log.debug(
        #     "_ instance.data: {}".format(pformat(instance.data)))
