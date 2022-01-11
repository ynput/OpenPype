import pyblish
# import openpype
import openpype.hosts.flame.api as opfapi

# # developer reload modules
from pprint import pformat


class PrecollectInstances(pyblish.api.ContextPlugin):
    """Collect all Track items selection."""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Precollect Instances"
    hosts = ["flame"]

    audio_track_items = []

    def process(self, context):
        project = context.data["flameProject"]
        sequence = context.data["flameSequence"]
        self.otio_timeline = context.data["otioTimeline"]
        self.clips_in_reels = opfapi.get_clips_in_reels(project)

        # return only actually selected and enabled segments
        selected_segments = opfapi.get_sequence_segments(sequence, True)

        # only return enabled segments
        if not selected_segments:
            selected_segments = opfapi.get_sequence_segments(
                sequence)

        self.log.info(
            "Processing following segments: {}".format(
                [s.name for s in selected_segments]))

        # process all sellected timeline track items
        for segment in selected_segments:

            clip_data = opfapi.get_segment_attributes(segment)
            clip_name = clip_data["segment_name"]
            self.log.debug("clip_name: {}".format(clip_name))

            # get openpype tag data
            marker_data = opfapi.get_segment_data_marker(segment)
            self.log.debug("__ marker_data: {}".format(pformat(marker_data)))

            if not marker_data:
                continue

            if marker_data.get("id") != "pyblish.avalon.instance":
                continue

            file_path = clip_data["fpath"]
            first_frame = opfapi.get_frame_from_path(file_path) or 0

            # calculate head and tail with forward compatibility
            head = clip_data.get("segment_head")
            tail = clip_data.get("segment_tail")

            if not head:
                head = int(clip_data["source_in"]) - int(first_frame)
            if not tail:
                tail = int(
                    clip_data["source_duration"] - (
                        head + clip_data["record_duration"]
                    )
                )

            # solve handles length
            marker_data["handleStart"] = min(
                marker_data["handleStart"], head)
            marker_data["handleEnd"] = min(
                marker_data["handleEnd"], tail)

            # add audio to families
            with_audio = False
            if marker_data.pop("audio"):
                with_audio = True

            # add tag data to instance data
            data = {
                k: v for k, v in marker_data.items()
                if k not in ("id", "applieswhole", "label")
            }

            asset = marker_data["asset"]
            subset = marker_data["subset"]

            # insert family into families
            family = marker_data["family"]
            families = [str(f) for f in marker_data["families"]]
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
                "item": segment,
                "families": families,
                "publish": marker_data["publish"],
                "fps": context.data["fps"],
            })

            # # otio clip data
            # otio_data = self.get_otio_clip_instance_data(segment) or {}
            # self.log.debug("__ otio_data: {}".format(pformat(otio_data)))
            # data.update(otio_data)
            # self.log.debug("__ data: {}".format(pformat(data)))

            # # add resolution
            # self.get_resolution_to_data(data, context)

            # create instance
            instance = context.create_instance(**data)

            # add colorspace data
            instance.data.update({
                "versionData": {
                    "colorspace": clip_data["colour_space"],
                }
            })

            # create shot instance for shot attributes create/update
            self.create_shot_instance(context, clip_name, **data)

            self.log.info("Creating instance: {}".format(instance))
            self.log.info(
                "_ instance.data: {}".format(pformat(instance.data)))

            if not with_audio:
                continue

            # add audioReview attribute to plate instance data
            # if reviewTrack is on
            if marker_data.get("reviewTrack") is not None:
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

    def create_shot_instance(self, context, clip_name, **data):
        master_layer = data.get("heroTrack")
        hierarchy_data = data.get("hierarchyData")
        asset = data.get("asset")

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

    # def get_otio_clip_instance_data(self, segment):
    #     """
    #     Return otio objects for timeline, track and clip

    #     Args:
    #         timeline_item_data (dict): timeline_item_data from list returned by
    #                                 resolve.get_current_timeline_items()
    #         otio_timeline (otio.schema.Timeline): otio object

    #     Returns:
    #         dict: otio clip object

    #     """
    #     ti_track_name = segment.parent().name()
    #     timeline_range = self.create_otio_time_range_from_timeline_item_data(
    #         segment)
    #     for otio_clip in self.otio_timeline.each_clip():
    #         track_name = otio_clip.parent().name
    #         parent_range = otio_clip.range_in_parent()
    #         if ti_track_name not in track_name:
    #             continue
    #         if otio_clip.name not in segment.name():
    #             continue
    #         if openpype.lib.is_overlapping_otio_ranges(
    #                 parent_range, timeline_range, strict=True):

    #             # add pypedata marker to otio_clip metadata
    #             for marker in otio_clip.markers:
    #                 if phiero.pype_tag_name in marker.name:
    #                     otio_clip.metadata.update(marker.metadata)
    #             return {"otioClip": otio_clip}

    #     return None

    # @staticmethod
    # def create_otio_time_range_from_timeline_item_data(segment):
    #     speed = segment.playbackSpeed()
    #     timeline = phiero.get_current_sequence()
    #     frame_start = int(segment.timelineIn())
    #     frame_duration = int(segment.sourceDuration() / speed)
    #     fps = timeline.framerate().toFloat()

    #     return hiero_export.create_otio_time_range(
    #         frame_start, frame_duration, fps)
