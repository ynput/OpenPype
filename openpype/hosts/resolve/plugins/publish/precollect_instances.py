from pprint import pformat

import pyblish

from openpype.pipeline.editorial import is_overlapping_otio_ranges

from openpype.hosts.resolve.api.lib import (
    get_current_timeline_items,
    get_timeline_item_pype_tag,
    publish_clip_color,
    get_publish_attribute,
    get_otio_clip_instance_data,
    create_otio_time_range_from_timeline_item_data
)


class PrecollectInstances(pyblish.api.ContextPlugin):
    """Collect all Track items selection."""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Precollect Instances"
    hosts = ["resolve"]

    audio_track_items = []

    def process(self, context):
        otio_timeline = context.data["otioTimeline"]
        selected_timeline_items = get_current_timeline_items(
            filter=True, selecting_color=publish_clip_color)

        self.log.info(
            "Processing enabled track items: {}".format(
                len(selected_timeline_items)))

        for timeline_item_data in selected_timeline_items:

            data = {}
            timeline_item = timeline_item_data["clip"]["item"]

            # get pype tag data
            tag_data = get_timeline_item_pype_tag(timeline_item)
            self.log.debug(f"__ tag_data: {pformat(tag_data)}")

            if not tag_data:
                continue

            if tag_data.get("id") != "pyblish.avalon.instance":
                continue

            media_pool_item = timeline_item.GetMediaPoolItem()
            source_duration = int(media_pool_item.GetClipProperty("Frames"))

            # solve handles length
            handle_start = min(
                tag_data["handleStart"], int(timeline_item.GetLeftOffset()))
            handle_end = min(
                tag_data["handleEnd"], int(
                    source_duration - timeline_item.GetRightOffset()))

            self.log.debug("Handles: <{}, {}>".format(handle_start, handle_end))

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

            data.update({
                "name": "{}_{}".format(asset, subset),
                "label": "{} {}".format(asset, subset),
                "asset": asset,
                "item": timeline_item,
                "families": ["clip"],
                "publish": get_publish_attribute(timeline_item),
                "fps": context.data["fps"],
                "handleStart": handle_start,
                "handleEnd": handle_end,
                "newAssetPublishing": True
            })

            # otio clip data
            otio_data = get_otio_clip_instance_data(
                otio_timeline, timeline_item_data) or {}
            data.update(otio_data)

            # add resolution
            self.get_resolution_to_data(data, context)

            # create instance
            instance = context.create_instance(**data)

            # create shot instance for shot attributes create/update
            self.create_shot_instance(context, timeline_item, **data)

            if not with_audio:
                continue

            # create audio subset instance
            self.create_audio_instance(
                context, otio_timeline, timeline_item_data, **data)

            # add audioReview attribute to plate instance data
            # if reviewTrack is on
            if tag_data.get("reviewTrack") is not None:
                instance.data["reviewAudio"] = True

            self.log.info("Creating instance: {}".format(instance))
            self.log.debug(
                "_ instance.data: {}".format(pformat(instance.data)))

    def get_resolution_to_data(self, data, context):
        assert data.get("otioClip"), "Missing `otioClip` data"

        # solve source resolution option
        if data.get("sourceResolution", None):
            otio_clip_metadata = data[
                "otioClip"].media_reference.metadata
            data.update({
                "resolutionWidth": otio_clip_metadata["width"],
                "resolutionHeight": otio_clip_metadata["height"],
                "pixelAspect": otio_clip_metadata["pixelAspect"]
            })
        else:
            otio_tl_metadata = context.data["otioTimeline"].metadata
            data.update({
                "resolutionWidth": otio_tl_metadata["width"],
                "resolutionHeight": otio_tl_metadata["height"],
                "pixelAspect": otio_tl_metadata["pixelAspect"]
            })

    def create_shot_instance(self, context, timeline_item, **data):
        hero_track = data.get("heroTrack")
        hierarchy_data = data.get("hierarchyData")

        if not hero_track:
            return

        if not hierarchy_data:
            return

        asset = data["asset"]
        subset = "shotMain"

        # insert family into families
        family = "shot"

        data.update({
            "name": "{}_{}".format(asset, subset),
            "label": "{} {}".format(asset, subset),
            "subset": subset,
            "asset": asset,
            "family": family,
            "families": [],
            "publish": get_publish_attribute(timeline_item)
        })

        context.create_instance(**data)

    def create_audio_instance(
        self, context, otio_timeline, timeline_item_data, **data
    ):
        master_layer = data.get("heroTrack")

        if not master_layer:
            return

        asset = data.get("asset")

        # test if any audio clips
        if not self.test_any_audio(timeline_item_data, otio_timeline):
            return

        asset = data["asset"]
        subset = "audioMain"

        data.update({
            "name": "{}_{}".format(asset, subset),
            "label": "{} {}".format(asset, subset),
            "subset": subset,
            "family": "audio",
            "families": ["clip"]
        })
        # remove review track attr if any
        data.pop("reviewTrack")

        # create instance
        instance = context.create_instance(**data)
        self.log.info("Creating instance: {}".format(instance))
        self.log.debug(
            "_ instance.data: {}".format(pformat(instance.data)))

    def test_any_audio(self, timeline_item_data, otio_timeline):
        """Test if any audio clip is overlapping with given clip."""

        # collect all audio tracks to class variable
        if not self.audio_track_items:
            for otio_clip in otio_timeline.each_clip():
                if otio_clip.parent().kind != "Audio":
                    continue
                self.audio_track_items.append(otio_clip)

        # get track item timeline range
        timeline_range = create_otio_time_range_from_timeline_item_data(
            timeline_item_data)

        # loop through audio track items and search for overlapping clip
        for otio_audio in self.audio_track_items:
            parent_range = otio_audio.range_in_parent()

            # if any overaling clip found then return True
            if is_overlapping_otio_ranges(
                    parent_range, timeline_range, strict=False):
                return True
