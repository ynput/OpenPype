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
import openpype


class CollectOcioSubsetResources(pyblish.api.InstancePlugin):
    """Get Resources for a subset version"""

    label = "Collect OTIO Subset Resources"
    order = pyblish.api.CollectorOrder - 0.57
    families = ["clip"]
    hosts = ["resolve"]

    def process(self, instance):
        if not instance.data.get("representations"):
            instance.data["representations"] = list()
        version_data = dict()

        # get basic variables
        otio_clip = instance.data["otioClip"]
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        # generate range in parent
        otio_src_range = otio_clip.source_range
        otio_avalable_range = otio_clip.available_range()
        trimmed_media_range = openpype.lib.trim_media_range(
            otio_avalable_range, otio_src_range)

        # calculate wth handles
        otio_src_range_handles = openpype.lib.otio_range_with_handles(
            otio_src_range, instance)
        trimmed_media_range_h = openpype.lib.trim_media_range(
            otio_avalable_range, otio_src_range_handles)

        # frame start and end from media
        s_frame_start, s_frame_end = openpype.lib.otio_range_to_frame_range(
            trimmed_media_range)
        a_frame_start, a_frame_end = openpype.lib.otio_range_to_frame_range(
            otio_avalable_range)
        a_frame_start_h, a_frame_end_h = openpype.lib.otio_range_to_frame_range(
            trimmed_media_range_h)

        # fix frame_start and frame_end frame to be in range of media
        if a_frame_start_h < a_frame_start:
            a_frame_start_h = a_frame_start

        if a_frame_end_h > a_frame_end:
            a_frame_end_h = a_frame_end

        # count the difference for frame_start and frame_end
        diff_start = s_frame_start - a_frame_start_h
        diff_end = a_frame_end_h - s_frame_end

        # add to version data start and end range data
        # for loader plugins to be correctly displayed and loaded
        version_data.update({
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "handleStart": diff_start,
            "handleEnd": diff_end,
            "fps": otio_avalable_range.start_time.rate
        })

        # change frame_start and frame_end values
        # for representation to be correctly renumbered in integrate_new
        frame_start -= diff_start
        frame_end += diff_end

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
                    [i for i in range(a_frame_start_h, (a_frame_end_h + 1))])

                self.log.debug(collection)
                repre = self._create_representation(
                    frame_start, frame_end, collection=collection)
            else:
                # in case it is file sequence but not new OTIO schema
                # `ImageSequenceReference`
                path = media_ref.target_url
                collection_data = openpype.lib.make_sequence_collection(
                    path, trimmed_media_range, metadata)
                self.staging_dir, collection = collection_data

                self.log.debug(collection)
                repre = self._create_representation(
                    frame_start, frame_end, collection=collection)
        else:
            dirname, filename = os.path.split(media_ref.target_url)
            self.staging_dir = dirname

            self.log.debug(path)
            repre = self._create_representation(
                frame_start, frame_end, file=filename)

        if repre:
            instance.data["versionData"] = version_data
            self.log.debug(">>>>>>>> version data {}".format(version_data))
            # add representation to instance data
            instance.data["representations"].append(repre)
            self.log.debug(">>>>>>>> {}".format(repre))

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
