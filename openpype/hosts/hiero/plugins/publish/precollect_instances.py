import pyblish
import openpype
from openpype.hosts.hiero import api as phiero
from openpype.hosts.hiero.api.otio import hiero_export
import hiero

# # developer reload modules
from pprint import pformat


class PrecollectInstances(pyblish.api.ContextPlugin):
    """Collect all Track items selection."""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Precollect Instances"
    hosts = ["hiero"]

    audio_track_items = []

    def process(self, context):
        self.otio_timeline = context.data["otioTimeline"]
        timeline_selection = phiero.get_timeline_selection()
        selected_timeline_items = phiero.get_track_items(
            selection=timeline_selection,
            check_tagged=True,
            check_enabled=True
        )

        # only return enabled track items
        if not selected_timeline_items:
            selected_timeline_items = phiero.get_track_items(
                check_enabled=True, check_tagged=True)

        self.log.info(
            "Processing enabled track items: {}".format(
                selected_timeline_items))

        # add all tracks subtreck effect items to context
        all_tracks = hiero.ui.activeSequence().videoTracks()
        tracks_effect_items = self.collect_sub_track_items(all_tracks)
        context.data["tracksEffectItems"] = tracks_effect_items

        # process all sellected timeline track items
        for track_item in selected_timeline_items:
            data = {}
            clip_name = track_item.name()
            source_clip = track_item.source()
            self.log.debug("clip_name: {}".format(clip_name))

            # get openpype tag data
            tag_data = phiero.get_track_item_pype_data(track_item)
            self.log.debug("__ tag_data: {}".format(pformat(tag_data)))

            if not tag_data:
                continue

            if tag_data.get("id") != "pyblish.avalon.instance":
                continue

            # get clips subtracks and anotations
            annotations = self.clip_annotations(source_clip)
            subtracks = self.clip_subtrack(track_item)
            self.log.debug("Annotations: {}".format(annotations))
            self.log.debug(">> Subtracks: {}".format(subtracks))

            # solve handles length
            tag_data["handleStart"] = min(
                tag_data["handleStart"], int(track_item.handleInLength()))
            tag_data["handleEnd"] = min(
                tag_data["handleEnd"], int(track_item.handleOutLength()))

            # add audio to families
            with_audio = False
            if tag_data.pop("audio"):
                with_audio = True

            # add tag data to instance data
            data.update({
                k: v for k, v in tag_data.items()
                if k not in ("id", "applieswhole", "label")
            })

            asset = tag_data["asset"]
            subset = tag_data["subset"]

            # insert family into families
            family = tag_data["family"]
            families = [str(f) for f in tag_data["families"]]
            families.insert(0, str(family))

            # form label
            label = asset
            if asset != clip_name:
                label += " ({})".format(clip_name)
            label += " {}".format(subset)
            label += " {}".format("[" + ", ".join(families) + "]")

            data.update({
                "name": "{}_{}".format(asset, subset),
                "label": label,
                "asset": asset,
                "item": track_item,
                "families": families,
                "publish": tag_data["publish"],
                "fps": context.data["fps"],

                # clip's effect
                "clipEffectItems": subtracks,
                "clipAnnotations": annotations
            })

            # otio clip data
            otio_data = self.get_otio_clip_instance_data(track_item) or {}
            self.log.debug("__ otio_data: {}".format(pformat(otio_data)))
            data.update(otio_data)
            self.log.debug("__ data: {}".format(pformat(data)))

            # add resolution
            self.get_resolution_to_data(data, context)

            # create instance
            instance = context.create_instance(**data)

            # add colorspace data
            instance.data.update({
                "versionData": {
                    "colorspace": track_item.sourceMediaColourTransform(),
                }
            })

            # create shot instance for shot attributes create/update
            self.create_shot_instance(context, **data)

            self.log.info("Creating instance: {}".format(instance))
            self.log.info(
                "_ instance.data: {}".format(pformat(instance.data)))

            if not with_audio:
                continue

            # create audio subset instance
            self.create_audio_instance(context, **data)

            # add audioReview attribute to plate instance data
            # if reviewTrack is on
            if tag_data.get("reviewTrack") is not None:
                instance.data["reviewAudio"] = True

    def get_resolution_to_data(self, data, context):
        assert data.get("otioClip"), "Missing `otioClip` data"

        # solve source resolution option
        if data.get("sourceResolution", None):
            otio_clip_metadata = data[
                "otioClip"].media_reference.metadata
            data.update({
                "resolutionWidth": otio_clip_metadata[
                        "openpype.source.width"],
                "resolutionHeight": otio_clip_metadata[
                    "openpype.source.height"],
                "pixelAspect": otio_clip_metadata[
                    "openpype.source.pixelAspect"]
            })
        else:
            otio_tl_metadata = context.data["otioTimeline"].metadata
            data.update({
                "resolutionWidth": otio_tl_metadata["openpype.timeline.width"],
                "resolutionHeight": otio_tl_metadata[
                    "openpype.timeline.height"],
                "pixelAspect": otio_tl_metadata[
                    "openpype.timeline.pixelAspect"]
            })

    def create_shot_instance(self, context, **data):
        master_layer = data.get("heroTrack")
        hierarchy_data = data.get("hierarchyData")
        asset = data.get("asset")
        item = data.get("item")
        clip_name = item.name()

        if not master_layer:
            return

        if not hierarchy_data:
            return

        asset = data["asset"]
        subset = "shotMain"

        # insert family into families
        family = "shot"

        # form label
        label = asset
        if asset != clip_name:
            label += " ({}) ".format(clip_name)
        label += " {}".format(subset)
        label += " [{}]".format(family)

        data.update({
            "name": "{}_{}".format(asset, subset),
            "label": label,
            "subset": subset,
            "asset": asset,
            "family": family,
            "families": []
        })

        instance = context.create_instance(**data)
        self.log.info("Creating instance: {}".format(instance))
        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))

    def create_audio_instance(self, context, **data):
        master_layer = data.get("heroTrack")

        if not master_layer:
            return

        asset = data.get("asset")
        item = data.get("item")
        clip_name = item.name()

        # test if any audio clips
        if not self.test_any_audio(item):
            return

        asset = data["asset"]
        subset = "audioMain"

        # insert family into families
        family = "audio"

        # form label
        label = asset
        if asset != clip_name:
            label += " ({}) ".format(clip_name)
        label += " {}".format(subset)
        label += " [{}]".format(family)

        data.update({
            "name": "{}_{}".format(asset, subset),
            "label": label,
            "subset": subset,
            "asset": asset,
            "family": family,
            "families": ["clip"]
        })
        # remove review track attr if any
        data.pop("reviewTrack")

        # create instance
        instance = context.create_instance(**data)
        self.log.info("Creating instance: {}".format(instance))
        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))

    def test_any_audio(self, track_item):
        # collect all audio tracks to class variable
        if not self.audio_track_items:
            for otio_clip in self.otio_timeline.each_clip():
                if otio_clip.parent().kind != "Audio":
                    continue
                self.audio_track_items.append(otio_clip)

        # get track item timeline range
        timeline_range = self.create_otio_time_range_from_timeline_item_data(
            track_item)

        # loop through audio track items and search for overlapping clip
        for otio_audio in self.audio_track_items:
            parent_range = otio_audio.range_in_parent()

            # if any overaling clip found then return True
            if openpype.lib.is_overlapping_otio_ranges(
                    parent_range, timeline_range, strict=False):
                return True

    def get_otio_clip_instance_data(self, track_item):
        """
        Return otio objects for timeline, track and clip

        Args:
            timeline_item_data (dict): timeline_item_data from list returned by
                                    resolve.get_current_timeline_items()
            otio_timeline (otio.schema.Timeline): otio object

        Returns:
            dict: otio clip object

        """
        ti_track_name = track_item.parent().name()
        timeline_range = self.create_otio_time_range_from_timeline_item_data(
            track_item)
        for otio_clip in self.otio_timeline.each_clip():
            track_name = otio_clip.parent().name
            parent_range = otio_clip.range_in_parent()
            if ti_track_name not in track_name:
                continue
            if otio_clip.name not in track_item.name():
                continue
            self.log.debug("__ parent_range: {}".format(parent_range))
            self.log.debug("__ timeline_range: {}".format(timeline_range))
            if openpype.lib.is_overlapping_otio_ranges(
                    parent_range, timeline_range, strict=True):

                # add pypedata marker to otio_clip metadata
                for marker in otio_clip.markers:
                    if phiero.pype_tag_name in marker.name:
                        otio_clip.metadata.update(marker.metadata)
                return {"otioClip": otio_clip}

        return None

    @staticmethod
    def create_otio_time_range_from_timeline_item_data(track_item):
        speed = track_item.playbackSpeed()
        timeline = phiero.get_current_sequence()
        frame_start = int(track_item.timelineIn())
        frame_duration = int(track_item.sourceDuration() / speed)
        fps = timeline.framerate().toFloat()

        return hiero_export.create_otio_time_range(
            frame_start, frame_duration, fps)

    @staticmethod
    def collect_sub_track_items(tracks):
        """
        Returns dictionary with track index as key and list of subtracks
        """
        # collect all subtrack items
        sub_track_items = {}
        for track in tracks:
            items = track.items()

            # skip if no clips on track > need track with effect only
            if items:
                continue

            # skip all disabled tracks
            if not track.isEnabled():
                continue

            track_index = track.trackIndex()
            _sub_track_items = phiero.flatten(track.subTrackItems())

            # continue only if any subtrack items are collected
            if not list(_sub_track_items):
                continue

            enabled_sti = []
            # loop all found subtrack items and check if they are enabled
            for _sti in _sub_track_items:
                # checking if not enabled
                if not _sti.isEnabled():
                    continue
                if isinstance(_sti, hiero.core.Annotation):
                    continue
                # collect the subtrack item
                enabled_sti.append(_sti)

            # continue only if any subtrack items are collected
            if not enabled_sti:
                continue

            # add collection of subtrackitems to dict
            sub_track_items[track_index] = enabled_sti

        return sub_track_items

    @staticmethod
    def clip_annotations(clip):
        """
        Returns list of Clip's hiero.core.Annotation
        """
        annotations = []
        subTrackItems = phiero.flatten(clip.subTrackItems())
        annotations += [item for item in subTrackItems if isinstance(
            item, hiero.core.Annotation)]
        return annotations

    @staticmethod
    def clip_subtrack(clip):
        """
        Returns list of Clip's hiero.core.SubTrackItem
        """
        subtracks = []
        subTrackItems = phiero.flatten(clip.parent().subTrackItems())
        for item in subTrackItems:
            if "TimeWarp" in item.name():
                continue
            # avoid all anotation
            if isinstance(item, hiero.core.Annotation):
                continue
            # # avoid all not anaibled
            if not item.isEnabled():
                continue
            subtracks.append(item)
        return subtracks
