import os
import pyblish
from pype.hosts import resolve

# # developer reload modules
from pprint import pformat


class CollectInstances(pyblish.api.ContextPlugin):
    """Collect all Track items selection."""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Collect Instances"
    hosts = ["resolve"]

    def process(self, context):
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

            source_path = os.path.normpath(
                clip_property["File Path"])
            source_name = clip_property["File Name"]
            self.log.debug(f"source_path: {source_path}")
            self.log.debug(f"source_name: {source_name}")

            # add tag data to instance data
            data.update({
                k: v for k, v in tag_data.items()
                if k not in ("id", "applieswhole", "label")
            })

            asset = tag_data["asset"]
            subset = tag_data["subset"]
            review = tag_data["review"]

            # insert family into families
            family = tag_data["family"]
            families = [str(f) for f in tag_data["families"]]
            families.insert(0, str(family))

            track = track_item_data["track"]["name"]
            base_name = os.path.basename(source_path)
            file_head = os.path.splitext(base_name)[0]
            source_first_frame = int(
                track_item.GetStart()
                - track_item.GetLeftOffset()
            )

            # apply only for feview and master track instance
            if review:
                families += ["review", "ftrack"]

            data.update({
                "name": "{} {} {}".format(asset, subset, families),
                "asset": asset,
                "item": track_item,
                "families": families,
                "publish": resolve.get_publish_attribute(track_item),
                # tags
                "tags": tag_data,

                # track item attributes
                "track": track,

                # source attribute
                "source": source_path,
                "sourcePath": source_path,
                "sourceFileHead": file_head,
                "sourceFirst": source_first_frame,
            })

            instance = context.create_instance(**data)

            self.log.info("Creating instance: {}".format(instance))
