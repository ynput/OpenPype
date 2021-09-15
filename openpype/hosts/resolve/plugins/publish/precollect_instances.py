import pyblish
from openpype.hosts import resolve

# # developer reload modules
from pprint import pformat


class PrecollectInstances(pyblish.api.ContextPlugin):
    """Collect all Track items selection."""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Precollect Instances"
    hosts = ["resolve"]

    def process(self, context):
        otio_timeline = context.data["otioTimeline"]
        selected_timeline_items = resolve.get_current_timeline_items(
            filter=True, selecting_color=resolve.publish_clip_color)

        self.log.info(
            "Processing enabled track items: {}".format(
                len(selected_timeline_items)))

        for timeline_item_data in selected_timeline_items:

            data = dict()
            timeline_item = timeline_item_data["clip"]["item"]

            # get pype tag data
            tag_data = resolve.get_timeline_item_pype_tag(timeline_item)
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

            data.update({
                "name": "{} {} {}".format(asset, subset, families),
                "asset": asset,
                "item": timeline_item,
                "families": families,
                "publish": resolve.get_publish_attribute(timeline_item),
                "fps": context.data["fps"],
                "handleStart": handle_start,
                "handleEnd": handle_end
            })

            # otio clip data
            otio_data = resolve.get_otio_clip_instance_data(
                otio_timeline, timeline_item_data) or {}
            data.update(otio_data)

            # add resolution
            self.get_resolution_to_data(data, context)

            # create instance
            instance = context.create_instance(**data)

            # create shot instance for shot attributes create/update
            self.create_shot_instance(context, timeline_item, **data)

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
            "name": "{} {} {}".format(asset, subset, family),
            "subset": subset,
            "asset": asset,
            "family": family,
            "families": [],
            "publish": resolve.get_publish_attribute(timeline_item)
        })

        context.create_instance(**data)
