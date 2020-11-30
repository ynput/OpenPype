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
            filter=True, selecting_color="Pink")

        self.log.info(
            "Processing enabled track items: {}".format(
                len(selected_track_items)))

        for track_item_data in selected_track_items:
            self.log.debug(pformat(track_item_data))
            data = dict()
            track_item = track_item_data["clip"]["item"]
            self.log.debug(track_item)
            # get pype tag data
            tag_parsed_data = resolve.get_track_item_pype_tag(track_item)
            self.log.debug(pformat(tag_parsed_data))

            if not tag_parsed_data:
                continue

            if tag_parsed_data.get("id") != "pyblish.avalon.instance":
                continue

            compound_source_prop = tag_parsed_data["sourceProperties"]
            self.log.debug(f"compound_source_prop: {compound_source_prop}")

            # source = track_item_data.GetMediaPoolItem()

            source_path = os.path.normpath(
                compound_source_prop["File Path"])
            source_name = compound_source_prop["File Name"]
            source_id = tag_parsed_data["sourceId"]
            self.log.debug(f"source_path: {source_path}")
            self.log.debug(f"source_name: {source_name}")
            self.log.debug(f"source_id: {source_id}")

            # add tag data to instance data
            data.update({
                k: v for k, v in tag_parsed_data.items()
                if k not in ("id", "applieswhole", "label")
            })

            asset = tag_parsed_data["asset"]
            subset = tag_parsed_data["subset"]
            review = tag_parsed_data["review"]

            # insert family into families
            family = tag_parsed_data["family"]
            families = [str(f) for f in tag_parsed_data["families"]]
            families.insert(0, str(family))

            track = tag_parsed_data["track_data"]["name"]
            base_name = os.path.basename(source_path)
            file_head = os.path.splitext(base_name)[0]
            # source_first_frame = int(file_info.startFrame())

            # apply only for feview and master track instance
            if review:
                families += ["review", "ftrack"]

            data.update({
                "name": "{} {} {}".format(asset, subset, families),
                "asset": asset,
                "item": track_item,
                "families": families,

                # tags
                "tags": tag_parsed_data,

                # track item attributes
                "track": track,

                # source attribute
                "source": source_path,
                "sourcePath": source_path,
                "sourceFileHead": file_head,
                # "sourceFirst": source_first_frame,
            })

            instance = context.create_instance(**data)

            self.log.info("Creating instance: {}".format(instance))
