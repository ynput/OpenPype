import pyblish
import openpype
from openpype.hosts.hiero import api as phiero
from openpype.hosts.hiero.otio import hiero_export

# # developer reload modules
from pprint import pformat


class PrecollectInstances(pyblish.api.ContextPlugin):
    """Collect all Track items selection."""

    order = pyblish.api.CollectorOrder - 0.59
    label = "Precollect Instances"
    hosts = ["hiero"]

    def process(self, context):
        otio_timeline = context.data["otioTimeline"]
        selected_timeline_items = phiero.get_track_items(
            selected=True, check_enabled=True, check_tagged=True)
        self.log.info(
            "Processing enabled track items: {}".format(
                selected_timeline_items))

        for track_item in selected_timeline_items:

            data = dict()
            clip_name = track_item.name()

            # get openpype tag data
            tag_data = phiero.get_track_item_pype_data(track_item)
            self.log.debug("__ tag_data: {}".format(pformat(tag_data)))

            if not tag_data:
                continue

            if tag_data.get("id") != "pyblish.avalon.instance":
                continue

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
                "fps": context.data["fps"]
            })

            # otio clip data
            otio_data = self.get_otio_clip_instance_data(
                otio_timeline, track_item) or {}
            self.log.debug("__ otio_data: {}".format(pformat(otio_data)))
            data.update(otio_data)
            self.log.debug("__ data: {}".format(pformat(data)))

            # add resolution
            self.get_resolution_to_data(data, context)

            # create instance
            instance = context.create_instance(**data)

            # create shot instance for shot attributes create/update
            self.create_shot_instance(context, **data)

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

        context.create_instance(**data)

    def get_otio_clip_instance_data(self, otio_timeline, track_item):
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
        for otio_clip in otio_timeline.each_clip():
            track_name = otio_clip.parent().name
            parent_range = otio_clip.range_in_parent()
            if ti_track_name not in track_name:
                continue
            if otio_clip.name not in track_item.name():
                continue
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
        timeline = phiero.get_current_sequence()
        frame_start = int(track_item.timelineIn())
        frame_duration = int(track_item.sourceDuration())
        fps = timeline.framerate().toFloat()

        return hiero_export.create_otio_time_range(
            frame_start, frame_duration, fps)
