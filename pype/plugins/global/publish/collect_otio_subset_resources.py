# TODO: this head doc string
"""
Requires:
    instance -> otio_clip

Optional:
    instance -> review

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
        otio_src_range_handles = pype.lib.otio_range_with_handles(
            otio_src_range, instance)
        trimmed_media_range = pype.lib.trim_media_range(
            otio_avalable_range, otio_src_range_handles)

        self.log.debug(
            "_ trimmed_media_range: {}".format(trimmed_media_range))

        media_ref = otio_clip.media_reference
        metadata = media_ref.metadata

        # check in two way if it is sequence
        if hasattr(otio.schema, "ImageSequenceReference"):
            # for OpenTimelineIO 0.13 and newer
            if isinstance(media_ref,
                          otio.schema.ImageSequenceReference):
                is_sequence = True
        else:
            # for OpenTimelineIO 0.12 and older
            if metadata.get("padding"):
                is_sequence = True

        first, last = pype.lib.otio_range_to_frame_range(
            trimmed_media_range)

        self.log.info(
            "first-last: {}-{}".format(first, last))

        if is_sequence:
            # file sequence way
            if hasattr(media_ref, "target_url_base"):
                dirname = media_ref.target_url_base
                head = media_ref.name_prefix
                tail = media_ref.name_suffix
                collection = clique.Collection(
                    head=head,
                    tail=tail,
                    padding=media_ref.frame_zero_padding
                )
                collection.indexes.update(
                    [i for i in range(first, (last + 1))])
                # TODO: add representation
                self.log.debug((dirname, collection))
            else:
                # in case it is file sequence but not new OTIO schema
                # `ImageSequenceReference`
                path = media_ref.target_url
                dir_path, collection = pype.lib.make_sequence_collection(
                    path, trimmed_media_range, metadata)

                # TODO: add representation
                self.log.debug((dir_path, collection))
        else:
            path = media_ref.target_url
            # TODO: add representation
            self.log.debug(path)
