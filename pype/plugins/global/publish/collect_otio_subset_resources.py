# TODO: this head doc string
"""
Requires:
    instance -> otio_clip

Provides:
    instance -> otioReviewClips
"""
import os
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
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        # get basic variables
        otio_clip = instance.data["otioClip"]

        # generate range in parent
        otio_src_range = otio_clip.source_range
        otio_avalable_range = otio_clip.available_range()
        otio_src_range_handles = pype.lib.otio_range_with_handles(
            otio_src_range, instance)
        trimmed_media_range = pype.lib.trim_media_range(
            otio_avalable_range, otio_src_range_handles)

        a_frame_start, a_frame_end = pype.lib.otio_range_to_frame_range(
            otio_avalable_range)

        frame_start, frame_end = pype.lib.otio_range_to_frame_range(
            trimmed_media_range)

        # fix frame_start and frame_end frame to be in range of
        if frame_start < a_frame_start:
            frame_start = a_frame_start

        if frame_end > a_frame_end:
            frame_end = a_frame_end

        instance.data.update({
            "frameStart": frame_start,
            "frameEnd": frame_end
        })

        self.log.debug(
            "_ otio_avalable_range: {}".format(otio_avalable_range))
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

        self.log.info(
            "frame_start-frame_end: {}-{}".format(frame_start, frame_end))

        if is_sequence:
            # file sequence way
            if hasattr(media_ref, "target_url_base"):
                self.staging_dir = media_ref.target_url_base
                head = media_ref.name_prefix
                tail = media_ref.name_suffix
                collection = clique.Collection(
                    head=head,
                    tail=tail,
                    padding=media_ref.frame_zero_padding
                )
                collection.indexes.update(
                    [i for i in range(frame_start, (frame_end + 1))])

                self.log.debug(collection)
                repre = self._create_representation(
                    frame_start, frame_end, collection=collection)
                self.log.debug(repre)
            else:
                # in case it is file sequence but not new OTIO schema
                # `ImageSequenceReference`
                path = media_ref.target_url
                collection_data = pype.lib.make_sequence_collection(
                    path, trimmed_media_range, metadata)
                self.staging_dir, collection = collection_data

                self.log.debug(collection)
                repre = self._create_representation(
                    frame_start, frame_end, collection=collection)
                self.log.debug(repre)
        else:
            dirname, filename = os.path.split(media_ref.target_url)
            self.staging_dir = dirname

            self.log.debug(path)
            repre = self._create_representation(
                frame_start, frame_end, file=filename)
            self.log.debug(repre)

        if repre:
            instance.data
            instance.data["representations"].append(repre)

    def _create_representation(self, start, end, **kwargs):
        """
        Creating representation data.

        Args:
            start (int): start frame
            end (int): end frame
            kwargs (dict): optional data

        Returns:
            dict: representation data
        """

        # create default representation data
        representation_data = {
            "frameStart": start,
            "frameEnd": end,
            "stagingDir": self.staging_dir
        }

        if kwargs.get("collection"):
            collection = kwargs.get("collection")
            files = [f for f in collection]
            ext = collection.format("{tail}")
            representation_data.update({
                "name": ext[1:],
                "ext": ext[1:],
                "files": files,
                "frameStart": start,
                "frameEnd": end,
            })
            return representation_data
        if kwargs.get("file"):
            file = kwargs.get("file")
            ext = os.path.splitext(file)[-1]
            representation_data.update({
                "name": ext[1:],
                "ext": ext[1:],
                "files": file,
                "frameStart": start,
                "frameEnd": end,
            })
            return representation_data
