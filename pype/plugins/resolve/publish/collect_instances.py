import pyblish
from pype.hosts import resolve

# # developer reload modules
from pprint import pformat


class CollectInstances(pyblish.api.ContextPlugin):
    """Collect all Track items selection."""

    order = pyblish.api.CollectorOrder - 0.59
    label = "Collect Instances"
    hosts = ["resolve"]

    def process(self, context):
        otio_timeline = context.data["otioTimeline"]
        selected_track_items = resolve.get_current_track_items(
            filter=True, selecting_color=resolve.publish_clip_color)

        self.log.info(
            "Processing enabled track items: {}".format(
                len(selected_track_items)))

        for track_item_data in selected_track_items:

            data = dict()
            track_item = track_item_data["clip"]["item"]

            # get pype tag data
            tag_data = resolve.get_track_item_pype_tag(track_item)
            self.log.debug(f"__ tag_data: {pformat(tag_data)}")

            if not tag_data:
                continue

            if tag_data.get("id") != "pyblish.avalon.instance":
                continue

            media_pool_item = track_item.GetMediaPoolItem()
            clip_property = media_pool_item.GetClipProperty()
            self.log.debug(f"clip_property: {clip_property}")

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
                "item": track_item,
                "families": families,
                "publish": resolve.get_publish_attribute(track_item)
            })

            # otio clip data
            otio_data = resolve.get_otio_clip_instance_data(
                otio_timeline, track_item_data) or {}
            data.update(otio_data)

            # add resolution
            self.get_resolution_to_data(data, context)

            # create instance
            instance = context.create_instance(**data)

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
                "resolutionHeight": otio_clip_metadata["height"]
            })
        else:
            otio_tl_metadata = context.data["otioTimeline"].metadata
            data.update({
                "resolutionWidth": otio_tl_metadata["width"],
                "resolutionHeight": otio_tl_metadata["height"]
            })
