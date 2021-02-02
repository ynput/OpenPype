from pyblish import api
import os
import clique
from pype.hosts.hiero.api import (
    is_overlapping, get_sequence_pattern_and_padding)


class CollectReview(api.InstancePlugin):
    """Collect review representation.
    """

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1022
    label = "Collect Review"
    hosts = ["hiero"]
    families = ["review"]

    def get_review_item(self, instance):
        """
        Get review clip track item from review track name

        Args:
            instance (obj): publishing instance

        Returns:
            hiero.core.TrackItem: corresponding track item

        Raises:
            Exception: description

        """
        review_track = instance.data.get("review")
        video_tracks = instance.context.data["videoTracks"]
        for track in video_tracks:
            if review_track not in track.name():
                continue
            for item in track.items():
                self.log.debug(item)
                if is_overlapping(item, self.main_clip):
                    self.log.debug("Winner is: {}".format(item))
                    break

        # validate the clip is fully converted with review clip
        assert is_overlapping(
            item, self.main_clip, strict=True), (
                "Review clip not cowering fully "
                "the clip `{}`").format(self.main_clip.name())

        return item

    def process(self, instance):
        tags = ["review", "ftrackreview"]

        # get reviewable item from `review` instance.data attribute
        self.main_clip = instance.data.get("item")
        self.rw_clip = self.get_review_item(instance)

        # let user know there is missing review clip and convert instance
        # back as not reviewable
        assert self.rw_clip, "Missing reviewable clip for '{}'".format(
            self.main_clip.name()
        )

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        # get review media main info
        rw_source = self.rw_clip.source().mediaSource()
        rw_source_duration = int(rw_source.duration())
        self.rw_source_path = rw_source.firstpath()
        rw_source_file_info = rw_source.fileinfos().pop()

        # define if review media is sequence
        is_sequence = bool(not rw_source.singleFile())
        self.log.debug("is_sequence: {}".format(is_sequence))

        # get handles
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # review timeline and source frame ranges
        rw_clip_in = int(self.rw_clip.timelineIn())
        rw_clip_out = int(self.rw_clip.timelineOut())
        self.rw_clip_source_in = int(self.rw_clip.sourceIn())
        self.rw_clip_source_out = int(self.rw_clip.sourceOut())
        rw_source_first = int(rw_source_file_info.startFrame())

        # calculate delivery source_in and source_out
        # main_clip_timeline_in - review_item_timeline_in + 1
        main_clip_in = self.main_clip.timelineIn()
        main_clip_out = self.main_clip.timelineOut()

        source_in_diff = main_clip_in - rw_clip_in
        source_out_diff = main_clip_out - rw_clip_out

        if source_in_diff:
            self.rw_clip_source_in += source_in_diff
        if source_out_diff:
            self.rw_clip_source_out += source_out_diff

        # review clip durations
        rw_clip_duration = (
            self.rw_clip_source_out - self.rw_clip_source_in) + 1
        rw_clip_duration_h = rw_clip_duration + (
            handle_start + handle_end)

        # add created data to review item data
        instance.data["reviewItemData"] = {
            "mediaDuration": rw_source_duration
        }

        file_dir = os.path.dirname(self.rw_source_path)
        file = os.path.basename(self.rw_source_path)
        ext = os.path.splitext(file)[-1]

        # detect if sequence
        if not is_sequence:
            # is video file
            files = file
        else:
            files = list()
            spliter, padding = get_sequence_pattern_and_padding(file)
            self.log.debug("_ spliter, padding: {}, {}".format(
                spliter, padding))
            base_name = file.split(spliter)[0]

            # define collection and calculate frame range
            collection = clique.Collection(base_name, ext, padding, set(range(
                int(rw_source_first + int(
                    self.rw_clip_source_in - handle_start)),
                int(rw_source_first + int(
                    self.rw_clip_source_out + handle_end) + 1))))
            self.log.debug("_ collection: {}".format(collection))

            real_files = os.listdir(file_dir)
            self.log.debug("_ real_files: {}".format(real_files))

            # collect frames to repre files list
            for item in collection:
                if item not in real_files:
                    self.log.debug("_ item: {}".format(item))
                    continue
                files.append(item)

            # add prep tag
            tags.extend(["prep", "delete"])

        # change label
        instance.data["label"] = "{0} - ({1})".format(
            instance.data["label"], ext
        )

        self.log.debug("Instance review: {}".format(instance.data["name"]))

        # adding representation for review mov
        representation = {
            "files": files,
            "stagingDir": file_dir,
            "frameStart": rw_source_first + self.rw_clip_source_in,
            "frameEnd": rw_source_first + self.rw_clip_source_out,
            "frameStartFtrack": int(
                self.rw_clip_source_in - handle_start),
            "frameEndFtrack": int(self.rw_clip_source_out + handle_end),
            "step": 1,
            "fps": instance.data["fps"],
            "name": "review",
            "tags": tags,
            "ext": ext[1:]
        }

        if rw_source_duration > rw_clip_duration_h:
            self.log.debug("Media duration higher: {}".format(
                (rw_source_duration - rw_clip_duration_h)))
            representation.update({
                "frameStart": rw_source_first + int(
                    self.rw_clip_source_in - handle_start),
                "frameEnd": rw_source_first + int(
                    self.rw_clip_source_out + handle_end),
                "tags": ["_cut-bigger", "prep", "delete"]
            })
        elif rw_source_duration < rw_clip_duration_h:
            self.log.debug("Media duration higher: {}".format(
                (rw_source_duration - rw_clip_duration_h)))
            representation.update({
                "frameStart": rw_source_first + int(
                    self.rw_clip_source_in - handle_start),
                "frameEnd": rw_source_first + int(
                    self.rw_clip_source_out + handle_end),
                "tags": ["prep", "delete"]
            })

        instance.data["representations"].append(representation)

        self.create_thumbnail(instance)

        self.log.debug(
            "Added representations: {}".format(
                instance.data["representations"]))

    def create_thumbnail(self, instance):
        source_file = os.path.basename(self.rw_source_path)
        spliter, padding = get_sequence_pattern_and_padding(source_file)

        if spliter:
            head, ext = source_file.split(spliter)
        else:
            head, ext = os.path.splitext(source_file)

        # staging dir creation
        staging_dir = os.path.dirname(
            self.rw_source_path)

        # get thumbnail frame from the middle
        thumb_frame = int(self.rw_clip_source_in + (
            (self.rw_clip_source_out - self.rw_clip_source_in) / 2))

        thumb_file = "{}thumbnail{}{}".format(head, thumb_frame, ".png")
        thumb_path = os.path.join(staging_dir, thumb_file)

        thumbnail = self.rw_clip.thumbnail(thumb_frame).save(
            thumb_path,
            format='png'
        )
        self.log.debug(
            "__ thumbnail: `{}`, frame: `{}`".format(thumbnail, thumb_frame))

        self.log.debug("__ thumbnail: {}".format(thumbnail))
        thumb_representation = {
            'files': thumb_file,
            'stagingDir': staging_dir,
            'name': "thumbnail",
            'thumbnail': True,
            'ext': "png"
        }
        instance.data["representations"].append(
            thumb_representation)

    def version_data(self, instance):
        transfer_data = [
            "handleStart", "handleEnd", "sourceIn", "sourceOut",
            "frameStart", "frameEnd", "sourceInH", "sourceOutH",
            "clipIn", "clipOut", "clipInH", "clipOutH", "asset",
            "track"
        ]

        version_data = dict()
        # pass data to version
        version_data.update({k: instance.data[k] for k in transfer_data})

        if 'version' in instance.data:
            version_data["version"] = instance.data["version"]

        # add to data of representation
        version_data.update({
            "colorspace": self.rw_clip.sourceMediaColourTransform(),
            "families": instance.data["families"],
            "subset": instance.data["subset"],
            "fps": instance.data["fps"]
        })
        instance.data["versionData"] = version_data
