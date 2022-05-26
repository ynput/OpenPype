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
import openpype.lib as oplib


class CollectOtioSubsetResources(pyblish.api.InstancePlugin):
    """Get Resources for a subset version"""

    label = "Collect OTIO Subset Resources"
    order = pyblish.api.CollectorOrder - 0.077
    families = ["clip"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, instance):

        if "audio" in instance.data["family"]:
            return

        if not instance.data.get("representations"):
            instance.data["representations"] = []

        if not instance.data.get("versionData"):
            instance.data["versionData"] = {}

        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # get basic variables
        otio_clip = instance.data["otioClip"]
        otio_avalable_range = otio_clip.available_range()
        media_fps = otio_avalable_range.start_time.rate
        available_duration = otio_avalable_range.duration.value

        # get available range trimmed with processed retimes
        retimed_attributes = oplib.get_media_range_with_retimes(
            otio_clip, handle_start, handle_end)
        self.log.debug(
            ">> retimed_attributes: {}".format(retimed_attributes))

        # break down into variables
        media_in = int(retimed_attributes["mediaIn"])
        media_out = int(retimed_attributes["mediaOut"])
        handle_start = int(retimed_attributes["handleStart"])
        handle_end = int(retimed_attributes["handleEnd"])

        # set versiondata if any retime
        version_data = retimed_attributes.get("versionData")

        if version_data:
            instance.data["versionData"].update(version_data)

        # convert to available frame range with handles
        a_frame_start_h = media_in - handle_start
        a_frame_end_h = media_out + handle_end

        # create trimmed otio time range
        trimmed_media_range_h = oplib.range_from_frames(
            a_frame_start_h, (a_frame_end_h - a_frame_start_h) + 1,
            media_fps
        )
        trimmed_duration = trimmed_media_range_h.duration.value

        self.log.debug("trimmed_media_range_h: {}".format(
            trimmed_media_range_h))
        self.log.debug("a_frame_start_h: {}".format(
            a_frame_start_h))
        self.log.debug("a_frame_end_h: {}".format(
            a_frame_end_h))

        # create frame start and end
        frame_start = instance.data["frameStart"]
        frame_end = frame_start + (media_out - media_in)

        # add to version data start and end range data
        # for loader plugins to be correctly displayed and loaded
        instance.data["versionData"].update({
            "fps": media_fps
        })

        if not instance.data["versionData"].get("retime"):
            instance.data["versionData"].update({
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "handleStart": handle_start,
                "handleEnd": handle_end,
            })
        else:
            instance.data["versionData"].update({
                "frameStart": frame_start,
                "frameEnd": frame_end
            })

        # change frame_start and frame_end values
        # for representation to be correctly renumbered in integrate_new
        frame_start -= handle_start
        frame_end += handle_end

        media_ref = otio_clip.media_reference
        metadata = media_ref.metadata

        is_sequence = None
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
                collection_data = oplib.make_sequence_collection(
                    path, trimmed_media_range_h, metadata)
                self.staging_dir, collection = collection_data

                self.log.debug(collection)
                repre = self._create_representation(
                    frame_start, frame_end, collection=collection)
        else:
            _trim = False
            dirname, filename = os.path.split(media_ref.target_url)
            self.staging_dir = dirname
            if trimmed_duration < available_duration:
                self.log.debug("Ready for Trimming")
                instance.data["families"].append("trim")
                instance.data["otioTrimmingRange"] = trimmed_media_range_h
                _trim = True

            self.log.debug(filename)
            repre = self._create_representation(
                frame_start, frame_end, file=filename, trim=_trim)

        if repre:
            # add representation to instance data
            instance.data["representations"].append(repre)
            self.log.debug(">>>>>>>> {}".format(repre))

        self.log.debug(instance.data)

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

        if kwargs.get("trim") is True:
            representation_data.update({
                "tags": ["trim"]
            })
        return representation_data
